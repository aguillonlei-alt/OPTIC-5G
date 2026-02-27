from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime
import os 

# ==========================================
# 1. OPTIC-5G HARDWARE & SPATIAL MAPPING
# ==========================================
# Verify these match your physical router layout!
ROUTER_IPS = [
    "192.168.1.241", # Index 0 (Sim R0): Physical R11 [ACCESS POINT]
    "192.168.1.254", # Index 1 (Sim R1): Physical R10
    "192.168.1.253", # Index 2 (Sim R2): Physical R9  
    "192.168.1.252", # Index 3 (Sim R3): Physical R8
    "192.168.1.251",   # Index 4 (Sim R4): Physical R7 
    "192.168.1.244", # Index 5 (Sim R5): Physical R6  
    "192.168.1.243", # Index 6 (Sim R6): Physical R5
    "192.168.1.240", # Index 7 (Sim R7): Physical R12
    "192.168.1.242", # Index 8 (Sim R8): Physical R13
    "192.168.1.248", # Index 9 (Sim R9): Physical R0  
    "192.168.1.238", # Index 10 (Sim R10): Physical R1
    "192.168.1.247", # Index 11 (Sim R11): Physical R2
    "192.168.1.239", # Index 12 (Sim R12): Physical R3
    "192.168.1.246", # Index 13 (Sim R13): Physical R14
    "192.168.1.245", # Index 14 (Sim R14): Physical R16
    "192.168.1.250", # Index 15 (Sim R15): Physical R15
    "SKIP"           # Index 16 (Sim R16): Physical R4
]

USERNAME = "OPTIC5G"
PASSWORD = "bseceoptic5g"
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
    wait = WebDriverWait(driver, 15)

    downloads_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
    file_path = os.path.join(downloads_folder, 'OPTIC5G_RF_Data.csv')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(file_path, "a") as log_file:
        log_file.write(f"\nTest Run:,{timestamp},Mask:,{QUANTUM_MASK}\n")
        log_file.write("Router Label,IP Address,Signal,Noise,SNR,Radio Target\n")

        for i in range(len(QUANTUM_MASK)):
            target_ip = ROUTER_IPS[i]
            target_state = QUANTUM_MASK[i]
            router_label = f"Sim_Index_{i}" 
            
            if target_ip == "SKIP":
                log_file.write(f"{router_label},NOT DEPLOYED,N/A,N/A,N/A,Skipping\n")
                print(f"[{router_label}] Skipping.")
                continue 

            print(f"\n[{router_label}] Accessing {target_ip}...")

            try:
                # 1. NAVIGATE AND LOG IN (Enter-Key Bypass)
                driver.get(f"https://{target_ip}")
                wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text']"))).send_keys(USERNAME)
                pwd_box = driver.find_element(By.XPATH, "//input[@type='password']")
                pwd_box.send_keys(PASSWORD)
                pwd_box.send_keys(Keys.RETURN) 

                # ==========================================
                # PHASE 1: DATA GATHERING (STATUS TAB)
                # ==========================================
                print(f"   -> Waiting for live RF load...")
                time.sleep(7) # Increased to ensure Signal numbers populate
                
                signal_xpath = "/html/body/div[1]/div/div[3]/div/div[4]/div/div[2]/div[2]/div/div/div[1]/div[1]/div[2]/div[1]/span[2]/pre"
                noise_xpath = "/html/body/div[1]/div/div[3]/div/div[4]/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div[1]/span[2]/pre"
                snr_xpath = "/html/body/div[1]/div/div[3]/div/div[4]/div/div[2]/div[2]/div/div/div[3]/div[2]/div[2]/div[1]/span[2]/pre"

                signal_value = wait.until(EC.presence_of_element_located((By.XPATH, signal_xpath))).text
                noise_value = wait.until(EC.presence_of_element_located((By.XPATH, noise_xpath))).text
                snr_value = wait.until(EC.presence_of_element_located((By.XPATH, snr_xpath))).text

                radio_text = 'ON' if target_state == '1' else 'OFF'
                log_file.write(f"{router_label},{target_ip},{signal_value},{noise_value},{snr_value},{radio_text}\n")
                print(f"   -> [DATA SAVED] SNR: {snr_value}")

                # ==========================================
                # PHASE 2: MASK APPLICATION (WIRELESS TAB)
                # ==========================================
                if target_ip == "192.168.1.253" and target_state == '0':
                    print(f"   -> [ARMOR ACTIVE] Access Point must stay ON.")
                    continue 

                print(f"   -> Transitioning to Wireless settings...")
                time.sleep(3) # Let the sidebar settle

                # Double-Targeting XPath for the Wireless link
                try:
                    wireless_tab = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'nav-item') and contains(., 'Wireless')]")))
                except:
                    wireless_tab = wait.until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Wireless")))
                
                # JS Click to bypass UI stalls
                driver.execute_script("arguments[0].click();", wireless_tab)
                
                print(f"   -> Waiting for Wireless page render...")
                time.sleep(5) # Crucial wait for the checkbox widget to load
                
                # Manage Radio Checkbox using dynamic ID bypass
                radio_checkbox = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox' and contains(@id, 'wl-ap-enable-checkbox')]"))) 
                is_checked = radio_checkbox.is_selected()

                if target_state == '0' and is_checked:
                    driver.execute_script("arguments[0].click();", radio_checkbox)
                    print(f"   -> [ACTION] Radio Disabled.")
                elif target_state == '1' and not is_checked:
                    driver.execute_script("arguments[0].click();", radio_checkbox)
                    print(f"   -> [ACTION] Radio Enabled.")

                # Final Apply
                apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Apply')]")))
                driver.execute_script("arguments[0].click();", apply_btn)
                print(f"   -> [SUCCESS] Settings applied to {target_ip}")
                time.sleep(4)

            except Exception as e:
                log_file.write(f"{router_label},{target_ip},ERROR,ERROR,ERROR,Failed\n")
                print(f"   -> [FAILED] Error occurred at {target_ip}: {e}")

    print(f"\n[COMPLETE] Results saved to: {file_path}")
    driver.quit()

if __name__ == "__main__":
    apply_quantum_mask_and_gather_data()
