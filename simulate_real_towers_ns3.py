# simulate_real_towers_ns3.py
import pandas as pd

# Load geocoded + projected tower data (real Manila towers)
df = pd.read_csv("data/manila_towers_xy.csv")

# Filter valid coordinates
df = df.dropna(subset=["x", "y"])

# Define default parameters for NS-3 import
df["txPower_dBm"] = 20
df["frequency_GHz"] = 5.0
df["bandwidth_MHz"] = 100
df["radius_m"] = 200  # approximate 5G cell radius

# Save as NS-3 readable CSV
df.to_csv("data/real_towers_ns3.csv", index=False)
print("✅ Exported real 5G tower layout to data/real_towers_ns3.csv")
