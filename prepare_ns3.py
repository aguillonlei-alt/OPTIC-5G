import pandas as pd
from pathlib import Path

# Input: XY coordinates exported from prepare_ns3.py
input_file = Path("../data/manila_towers_xy.csv")
output_file = Path("../data/real_towers_ns3.csv")

# Load CSV
df = pd.read_csv(input_file)

# Add NS-3 simulation parameters
df["txPower_dBm"] = 20          # transmit power
df["frequency_GHz"] = 3.5       # typical 5G frequency
df["bandwidth_MHz"] = 100       # bandwidth per cell
df["radius_m"] = 250            # cell radius for visualization

# Save NS-3 ready CSV
df.to_csv(output_file, index=False)
print(f"✅ Exported NS-3 ready tower layout → {output_file}")
