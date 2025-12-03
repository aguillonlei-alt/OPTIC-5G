#!/usr/bin/env python3
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle
import contextily as ctx

# 1. Load Data
file_path = "data/manila_towers_geocoded_fixed.csv"
try:
    df = pd.read_csv(file_path)
except FileNotFoundError:
    print(f"File not found: {file_path}")
    exit()

# 2. Filter for Manila Area (Fixes "Zoomed Out" issue)
# Manila approx bounds: Lat 14.5 to 14.7, Lon 120.9 to 121.1
df = df[ (df['latitude'] > 14.50) & (df['latitude'] < 14.75) ]
df = df[ (df['longitude'] > 120.90) & (df['longitude'] < 121.15) ]

if len(df) == 0:
    print("Error: No towers found inside Manila bounds. Check your CSV coordinates.")
    exit()

# Convert to WebMercator for Plotting
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs="EPSG:4326")
gdf = gdf.to_crs(epsg=3857)

# 3. Setup Plot
fig, ax = plt.subplots(figsize=(15, 15))

# Smart Zoom: Use the bounds of the filtered data + buffer
minx, miny, maxx, maxy = gdf.total_bounds
buffer = 1000 # 1km buffer
ax.set_xlim(minx - buffer, maxx + buffer)
ax.set_ylim(miny - buffer, maxy + buffer)

# 4. Draw Towers
print(f"--> Plotting {len(gdf)} towers in Manila...")
count_dir = 0

for idx, row in gdf.iterrows():
    x, y = row.geometry.x, row.geometry.y
    azimuth = row.get('azimuth_deg', float('nan'))
    
    # Force visible radius for the map
    vis_radius = 600.0 

    if pd.notna(azimuth):
        count_dir += 1
        # Convert Compass (CW North) to Math (CCW East)
        center_angle = 90 - azimuth
        patch = Wedge((x, y), vis_radius, center_angle - 30, center_angle + 30, 
                      color='blue', alpha=0.5, width=vis_radius)
        ax.add_patch(patch)
    else:
        patch = Circle((x, y), vis_radius/2, color='red', alpha=0.5)
        ax.add_patch(patch)

# Add center dots
gdf.plot(ax=ax, color='black', markersize=10, zorder=10)

# 5. Background Map
try:
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
except:
    print("No internet for map tiles.")

ax.set_title(f"OPTIC-5G Manila: {count_dir} Directional / {len(gdf)} Total", fontsize=16)
ax.set_axis_off()
plt.tight_layout()

output_file = "data/manila_towers_visualization.png"
plt.savefig(output_file, dpi=300)
print(f"Saved Map: {output_file}")
