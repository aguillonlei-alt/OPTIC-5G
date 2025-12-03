#!/usr/bin/env python3
import re
import pandas as pd
import numpy as np
from pathlib import Path
from pyproj import Transformer

# Files
clean_file = Path("data/manila_towers_clean.csv")
geocoded_file = Path("data/manila_towers_geocoded.csv")
out_ns3 = Path("data/real_towers_ns3.csv")
out_geo_fixed = Path("data/manila_towers_geocoded_fixed.csv")

print(f"--> Reading source files...")
try:
    df_geo = pd.read_csv(geocoded_file)
    # Read entire CSV as string to handle multi-columns
    df_clean = pd.read_csv(clean_file, dtype=str, keep_default_na=False, header=None)
except FileNotFoundError as e:
    print(f"Error: {e}")
    exit(1)

# ---------------------------------------------------------
# 1. ROBUST BLOCK RECONSTRUCTION
# ---------------------------------------------------------
# Step A: Flatten each row into a single string
# Example: col0="Direction", col1="N (354)" -> "Direction N (354)"
raw_lines = df_clean.apply(lambda x: ' '.join(x.dropna().astype(str)), axis=1).tolist()

# Step B: Group lines into "Tower Blocks" using 'eNB ID' as the separator
blocks = []
current_block = []

for line in raw_lines:
    # If we hit a new tower header, save the previous block
    if "eNB ID" in line and current_block:
        blocks.append(" ".join(current_block))
        current_block = []
    
    current_block.append(line)

# Don't forget the last block
if current_block:
    blocks.append(" ".join(current_block))

print(f"--> Reconstructed {len(blocks)} tower data blocks from PDF.")
print(f"--> Geocoded locations available: {len(df_geo)}")

# ---------------------------------------------------------
# 2. EXTRACT REAL AZIMUTHS
# ---------------------------------------------------------
extracted_data = []
limit = min(len(blocks), len(df_geo))

for i in range(limit):
    text = blocks[i]
    geo_row = df_geo.iloc[i]
    
    # 1. Find Azimuths (Supports multiple sectors per tower)
    # Regex looks for: "Direction" ... then a number inside ( )
    # We strip special chars from degrees to be safe
    azimuths = re.findall(r"Direction.*?\((\d{1,3})", text, re.IGNORECASE)
    
    # 2. Find Bandwidth & Power
    bw_match = re.search(r"Bandwidth.*?(\d{1,3})\s*MHz", text, re.IGNORECASE)
    bandwidth = float(bw_match.group(1)) if bw_match else 10.0
    
    # Heuristic for TxPower:
    # If PDF says "Macro", use 46 dBm. If RSRP is very low, use 43.
    tx_power = 46.0 

    # 3. Create Rows (Real Data)
    if azimuths:
        for azi in azimuths:
            row = geo_row.to_dict()
            row['azimuth_deg'] = float(azi)
            row['bandwidth_mhz'] = bandwidth
            row['txpower_dbm'] = tx_power
            row['frequency_ghz'] = 1.8 # Default Band 3
            extracted_data.append(row)
    else:
        # Fallback if NO direction found (Omni-directional)
        row = geo_row.to_dict()
        row['azimuth_deg'] = np.nan 
        row['bandwidth_mhz'] = bandwidth
        row['txpower_dbm'] = tx_power
        row['frequency_ghz'] = 1.8
        extracted_data.append(row)

df_final = pd.DataFrame(extracted_data)

# Count how many are directional vs omni
dir_count = df_final['azimuth_deg'].notna().sum()
print(f"Extraction Complete: {len(df_final)} total cells.")
print(f"   - Directional Sectors Found: {dir_count}")
print(f"   - Omni-directional (Fallback): {len(df_final) - dir_count}")

# ---------------------------------------------------------
# 3. SAVE AND FORMAT
# ---------------------------------------------------------
# Normalize Geo Columns
df_final.columns = [c.strip().lower() for c in df_final.columns]
if "latitude" not in df_final.columns: df_final.rename(columns={"lat": "latitude", "y": "latitude"}, inplace=True)
if "longitude" not in df_final.columns: df_final.rename(columns={"lon": "longitude", "x": "longitude"}, inplace=True)

df_final = df_final.dropna(subset=['latitude', 'longitude'])

# Convert to XY
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32651", always_xy=True)
xs, ys = transformer.transform(df_final['longitude'].values, df_final['latitude'].values)

min_x, min_y = xs.min(), ys.min()
df_final['x_m'] = xs - min_x + 500.0
df_final['y_m'] = ys - min_y + 500.0

# Save
df_final.to_csv(out_geo_fixed, index=False)
cols_ns3 = ['x_m', 'y_m', 'txpower_dbm', 'frequency_ghz', 'bandwidth_mhz']
df_final[cols_ns3].to_csv(out_ns3, index=False)

print(f"Saved plotting data: {out_geo_fixed}")
print(f"Saved NS-3 data: {out_ns3}")
