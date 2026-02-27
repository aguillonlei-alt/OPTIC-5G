from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
import os # Added to dynamically find your Downloads folder!

# ==========================================
# 1. OPTIC-5G HARDWARE & SPATIAL MAPPING
# ==========================================
ROUTER_IPS = [
    "192.168.1.254", # Index 0  (Sim R0):  Physical R11 [ACCESS POINT]
    "192.168.1.251", # Index 1  (Sim R1):  Physical R10
    "192.168.1.252", # Index 2  (Sim R2):  Physical R9  <-- WARNING: DUPLICATE IP
    "192.168.1.250", # Index 3  (Sim R3):  Physical R8
    "192.168.1.248", # Index 4  (Sim R4):  Physical R7
    "192.168.1.246", # Index 5  (Sim R5):  Physical R6  
    "192.168.1.247", # Index 6  (Sim R6):  Physical R5
    "192.168.1.241", # Index 7  (Sim R7):  Physical R12
    "192.168.1.243", # Index 8  (Sim R8):  Physical R13
    "192.168.1.252", # Index 9  (Sim R9):  Physical R0  <-- WARNING: DUPLICATE IP
    "192.168.1.242", # Index 10 (Sim R10): Physical R1
    "192.168.1.238", # Index 11 (Sim R11): Physical R2
    "192.168.1.239", # Index 12 (Sim R12): Physical R3
    "192.168.1.245", # Index 13 (Sim R13): Physical R14
    "192.168.1.244", # Index 14 (Sim R14): Physical R16
    "192.168.1.240", # Index 15 (Sim R15): Physical R15
    "SKIP"           # Index 16 (Sim R16): Physical R4 [NOT DEPLOYED]
]

# TP-Link PharOS Login Credentials
USERNAME = "OPTIC5G"
PASSWORD = "bseceoptic5g"

# Paste your exact 17-digit mask from the quantum simulation here!
QUANTUM_MASK = "11111111111111111"

# ==========================================
# 2. SELENIUM CONFIGURATION
# ==========================================
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--ignore-certificate-errors") 
    chrome_options.add_argument("--incognito")
    return webdriver.Chrome(options=chrome_options)

# ==========================================
# 3. THE EXECUTION LOOP
# ==========================================
def apply_quantum_mask_and_gather_data():
    if len(QUANTUM_MASK) != len(ROUTER_IPS):
        print(f"ERROR: Mask length does not match array length!")
        return

    driver = setup_driver()
    wait = WebDriverWait(driver, 10)

    # --- THE MAGIC DOWNLOADS PATH ---
    downloads_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
    file_path = os.path.join(downloads_folder, 'OPTIC5G_RF_Data.csv')
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(file_path, "a") as log_file:
        # Write the CSV Headers
        log_file.write(f"\nTest Run:,{timestamp},Mask:,{QUANTUM_MASK}\n")
        log_file.write("Router Label,IP Address,SNR,Noise,Radio Target\n")

        for i in range(len(QUANTUM_MASK)):
            target_ip = ROUTER_IPS[i]
            target_state = QUANTUM_MASK[i]
            router_label = f"Sim_Index_{i}" 
            
            if target_ip == "SKIP":
                log_file.write(f"{router_label},NOT DEPLOYED,N/A,N/A,Skipping\n")
                print(f"[{router_label}] Physical router NOT DEPLOYED. Skipping.")
                continue 

            print(f"\n[{router_label}] Accessing {target_ip}...")

            try:
                # 1. Navigate and Log In 
                driver.get(f"https://{target_ip}")
                wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
                driver.find_element(By.ID, "password").send_keys(PASSWORD)
                driver.find_element(By.ID, "login-btn").click() 

                # ==========================================
                # PHASE 1: AUTOMATED DATA GATHERING
                # ==========================================
                print(f"   -> Scraping RF Data from Status Tab...")
                
                # SNR XPath
                snr_value = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[3]/div/div[4]/div/div[2]/div[2]/div/div/div[3]/div[2]/div[2]/div[1]/span[2]/pre"))).text
                
                # NEW: Noise Strength XPath!
                noise_value = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[3]/div/div[4]/div/div[2]/div[2]/div/div/div[1]/div[1]/div[2]/div[1]/span[2]/pre"))).text

                # Format as comma-separated values
                radio_text = 'ON' if target_state == '1' else 'OFF'
                data_string = f"{router_label},{target_ip},{snr_value},{noise_value},{radio_text}\n"
                
                log_file.write(data_string)
                print(f"   -> [DATA SAVED] SNR: {snr_value} | Noise: {noise_value}")

                # ==========================================
                # PHASE 2: EXECUTION & MASK APPLICATION
                # ==========================================
                if target_ip == "192.168.1.254" and target_state == '0':
                    print(f"   -> [ARMOR ACTIVE] Cannot turn off the Access Point. Leaving Radio ON.")
                    continue 

                # Click to Wireless Tab 
                wait.until(EC.element_to_be_clickable((By.ID, "menu-wireless"))).click() 
                
                # Check Radio box status 
                radio_checkbox = wait.until(EC.presence_of_element_located((By.ID, "enable-radio-checkbox"))) 
                is_checked = radio_checkbox.is_selected()

                if target_state == '0' and is_checked:
                    radio_checkbox.click() 
                    print(f"   -> [ACTION] Radio Disabled. Interference cleared.")
                elif target_state == '1' and not is_checked:
                    radio_checkbox.click() 
                    print(f"   -> [ACTION] Radio Enabled. Beam active.")
                else:
                    print(f"   -> [ACTION] Radio already in correct state.")

                # Apply and Save 
                driver.find_element(By.ID, "apply-btn").click()
                time.sleep(2) 
                driver.find_element(By.ID, "save-config-btn").click() 
                time.sleep(3) 

            except Exception as e:
                error_msg = f"{router_label},{target_ip},ERROR,ERROR,Connection Failed\n"
                log_file.write(error_msg)
                print(f"   -> [FAILED] Could not connect or find elements.")

    print(f"\n[COMPLETE] Data saved directly to: {file_path}")
    driver.quit()

if __name__ == "__main__":
    apply_quantum_mask_and_gather_data()
