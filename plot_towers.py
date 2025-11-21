import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import contextily as ctx
from pathlib import Path

# --------[ CONFIG ]--------
data_dir = Path("../data")
xy_file = data_dir / "manila_towers_xy.csv"
geo_file = data_dir / "manila_towers_geocoded.csv"
csv_path = None

if xy_file.is_file():
    csv_path = xy_file
    print(f"🗂️ Using XY file: {xy_file}")
elif geo_file.is_file():
    csv_path = geo_file
    print(f"🗂️ Using geocoded file: {geo_file}")
else:
    raise FileNotFoundError("No data file found in ../data/ directory.")

df = pd.read_csv(csv_path)

# --------[ GET THE RIGHT COORDINATES ]--------
if {'x_m', 'y_m'}.issubset(df.columns):
    x_col, y_col = 'x_m', 'y_m'
    plot_crs = "EPSG:32651"   # UTM Zone 51N
    print("Coordinates: x_m/y_m (meters)")
else:
    lat_col = next((c for c in df.columns if "lat" in c.lower()), None)
    lon_col = next((c for c in df.columns if "lon" in c.lower() or "long" in c.lower()), None)
    if not lat_col or not lon_col:
        raise ValueError("No latitude/longitude columns found!")
    x_col, y_col = lon_col, lat_col
    plot_crs = "EPSG:4326"
    print(f"Coordinates: {lat_col}, {lon_col} (degrees)")

gdf = gpd.GeoDataFrame(
    df, 
    geometry=[Point(xy) for xy in zip(df[x_col], df[y_col])],
    crs=plot_crs
)

# Convert CRS to Web Mercator
gdf = gdf.to_crs(epsg=3857)

fig, ax = plt.subplots(figsize=(10, 10))

# Focus on Manila only
manila_xmin, manila_xmax = 13457300, 13475000
manila_ymin, manila_ymax = 1635000, 1650000
ax.set_xlim(manila_xmin, manila_xmax)
ax.set_ylim(manila_ymin, manila_ymax)

signal_radius = 750  # meters

# Plot signal radius at each tower
for geom in gdf.geometry:
    circle = plt.Circle(
        (geom.x, geom.y), 
        radius=signal_radius, 
        facecolor='blue', edgecolor='blue', alpha=0.10
    )
    ax.add_patch(circle)

ax.scatter(
    [geom.x for geom in gdf.geometry], 
    [geom.y for geom in gdf.geometry], 
    color="red", s=30, zorder=10, label="Tower"
)

ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=15)

plt.title("5G/LTE Tower Locations in Manila (+ signal radius)", fontweight="bold")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.legend(loc="upper right")

out_png = data_dir / "manila_towers_plot.png"
plt.savefig(out_png, dpi=300, bbox_inches="tight")
print(f"✅ Plot saved to {out_png}")
