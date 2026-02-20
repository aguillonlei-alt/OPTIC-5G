import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.patches import Wedge, Circle

# ==========================================
# 1. CONFIGURATION
# ==========================================
FILE_PATH = "data/manila_towers_geocoded_fixed.csv"
OUTPUT_FILE = "data/optic5g_manila_zoom.png"

# 🔴 PASTE YOUR MASK STRING HERE
PLOT_STRING = "100101010010000000000000101000001000100000000101000000000001000000000000000110000000000000000000000000000000000000000000000000001000000010000000000000100000000010000001000000001000000000000000000000000000000000000100000000001000000000000000000"

# Visualization Settings
BEAM_RADIUS = 1200  
BEAM_WIDTH = 60     

# ==========================================
# 2. DATA PREPARATION
# ==========================================
print(f"--> Loading Data from {FILE_PATH}...")
try:
    df = pd.read_csv(FILE_PATH)
    print(f"--> Initial Data Rows: {len(df)}")
except FileNotFoundError:
    print("❌ Error: Data file not found.")
    exit()

# 🔴 FIX: REMOVED THE SEA FILTER
# We do NOT filter rows here anymore. We need all 243 rows to match the 243 characters in your mask.
# The mask itself has '0' for the sea towers, so they will automatically be plotted as "Inactive".

# Validate Mask Length
if len(PLOT_STRING) != len(df):
    print(f"⚠️ Warning: Length mismatch. Data: {len(df)}, String: {len(PLOT_STRING)}")
    if len(PLOT_STRING) > len(df):
        PLOT_STRING = PLOT_STRING[:len(df)]
    else:
        PLOT_STRING = PLOT_STRING.ljust(len(df), '0')

df['status'] = [x for x in PLOT_STRING]

# Convert to Web Mercator (EPSG:3857)
gdf = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs="EPSG:4326"
).to_crs(epsg=3857)

# ==========================================
# 3. FORCED MANILA BOUNDS
# ==========================================
MANILA_MIN_X = 1.3465e7
MANILA_MAX_X = 1.3485e7
MANILA_MIN_Y = 1.6350e6  
MANILA_MAX_Y = 1.6550e6  

xlim = (MANILA_MIN_X, MANILA_MAX_X)
ylim = (MANILA_MIN_Y, MANILA_MAX_Y)

# Calculate Aspect Ratio
x_span = xlim[1] - xlim[0]
y_span = ylim[1] - ylim[0]
aspect_ratio = y_span / x_span

# Set Figure Size
fig_width = 15
fig_height = fig_width * aspect_ratio
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

# ==========================================
# 4. PLOTTING
# ==========================================
active_towers = gdf[gdf['status'] == '1']
inactive_towers = gdf[gdf['status'] == '0']

# A. Plot Inactive (Gray Dots)
inactive_towers.plot(ax=ax, color='gray', alpha=0.3, markersize=30, zorder=1)

# B. Plot Active Towers (Green Sectors) AND Count Visible
visible_count = 0

for idx, row in active_towers.iterrows():
    # Check if inside View Box
    if (row.geometry.x >= xlim[0] and row.geometry.x <= xlim[1] and 
        row.geometry.y >= ylim[0] and row.geometry.y <= ylim[1]):
        
        visible_count += 1 
        
        x, y = row.geometry.x, row.geometry.y
        azimuth = row['azimuth_deg']
        
        if pd.notna(azimuth):
            center_angle = 90 - azimuth
            wedge = Wedge((x, y), BEAM_RADIUS, center_angle - 30, center_angle + 30, 
                          color='#00FF00', alpha=0.6, zorder=10)
            ax.add_patch(wedge)
            ax.scatter(x, y, c='black', s=80, zorder=11)
        else:
            circle = Circle((x, y), BEAM_RADIUS * 0.7, color='#00FF00', alpha=0.4, zorder=10)
            ax.add_patch(circle)
            ax.scatter(x, y, c='lime', edgecolors='black', s=150, zorder=11)

        ax.text(x, y + 250, str(idx), fontsize=14, fontweight='bold', ha='center', zorder=15)

# Hack for Legend
ax.scatter([], [], c='#00FF00', s=300, label='OPTIC-5G Active', edgecolor='black')

# APPLY THE FORCED LOCK
ax.set_xlim(xlim)
ax.set_ylim(ylim)
ax.set_axis_off()

# Add Map Tiles
try:
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
except Exception:
    print("⚠️ Warning: Could not download map tiles.")

# TITLE
total_active = len(active_towers)
plt.title(f"OPTIC-5G: Manila Focus\nActive: {visible_count} Visible (Total {total_active} Active)", 
          fontsize=20, fontweight='bold')
plt.legend(loc='upper right', fontsize=15)

plt.tight_layout()
plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', pad_inches=0.1)
print(f"✅ Map Saved: {OUTPUT_FILE}")
