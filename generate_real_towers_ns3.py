import pandas as pd
from pathlib import Path

# Input and output files
geo_file = Path("../data/manila_towers_geocoded.csv")
xy_file = Path("../data/manila_towers_xy.csv")
output_file = Path("../data/real_towers_ns3.csv")

# Pick best available source
if xy_file.is_file():
    print(f"Using XY source: {xy_file}")
    df = pd.read_csv(xy_file)

elif geo_file.is_file():
    print(f"Using geocoded source: {geo_file}")
    df = pd.read_csv(geo_file)
else:
    raise FileNotFoundError("❌ No geocoded/XY file found in ../data/")

# -------------------------------------------
# AUTO-DETECT coordinate columns
# -------------------------------------------
lat_cols = [c for c in df.columns if "lat" in c.lower()]
lon_cols = [c for c in df.columns if "lon" in c.lower()]

if {"x_m", "y_m"}.issubset(df.columns):
    # Already converted to meters
    df["x"] = df["x_m"]
    df["y"] = df["y_m"]

elif lat_cols and lon_cols:
    # Use lat/lon directly (coordinates will be small — ok for NS-3)
    df["x"] = df[lon_cols[0]]
    df["y"] = df[lat_cols[0]]

else:
    raise ValueError("❌ No coordinate columns detected!")

# -------------------------------------------
# FORCE numeric parsing (robust)
# -------------------------------------------
numeric_fields = {
    "txPower_dBm": 20.0,
    "frequency_GHz": 3.5,
    "bandwidth_MHz": 100.0,
    "radius_m": 250.0
}

for col, default in numeric_fields.items():
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)
    else:
        df[col] = default

# -------------------------------------------
# Save final NS3-ready CSV
# -------------------------------------------
output_file.parent.mkdir(parents=True, exist_ok=True)
df[["x", "y", "txPower_dBm", "frequency_GHz", "bandwidth_MHz", "radius_m"]].to_csv(output_file, index=False)

print(f"✅ Generated: {output_file}")
