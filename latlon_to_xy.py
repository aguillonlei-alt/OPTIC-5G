import pandas as pd
from pyproj import Transformer
from pathlib import Path

# Input and output files
input_file = Path("data/manila_towers_geocoded.csv")
output_file = Path("data/manila_towers_xy.csv")

# Read the geocoded data
df = pd.read_csv(input_file)

# Check column names
lat_cols = [c for c in df.columns if "lat" in c.lower()]
lon_cols = [c for c in df.columns if "lon" in c.lower() or "long" in c.lower()]

if not lat_cols or not lon_cols:
    raise ValueError("❌ No latitude/longitude columns found in file.")

lat_col, lon_col = lat_cols[0], lon_cols[0]
print(f"Using columns: {lat_col} (lat), {lon_col} (lon)")

# Manila → UTM Zone 51N projection
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32651", always_xy=True)
xs, ys = transformer.transform(df[lon_col].values, df[lat_col].values)

df["x_m"] = xs
df["y_m"] = ys

df.to_csv(output_file, index=False)
print("✅ Saved", output_file, "with x_m,y_m in meters (UTM Zone 51N).")
