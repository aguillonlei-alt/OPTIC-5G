import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

df = pd.read_csv(Path("data/manila_towers_xy.csv"))

plt.figure(figsize=(8,8))
plt.scatter(df["x_m"], df["y_m"], s=10)
plt.title("5G Macro Tower Distribution – Manila")
plt.xlabel("X (meters, UTM Zone 51N)")
plt.ylabel("Y (meters, UTM Zone 51N)")
plt.grid(True)
plt.axis('equal')

# Save instead of show
plt.tight_layout()
plt.savefig("data/manila_towers_plot.png", dpi=300)
print("✅ Saved tower map to data/manila_towers_plot.png")
