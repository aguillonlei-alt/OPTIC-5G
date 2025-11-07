import numpy as np, pandas as pd

# Campus / city area bounds (meters, UTM Zone 51N)
x_min, x_max = 278000, 290000
y_min, y_max = 1606000, 1618000
radius = 50  # 50 m cell radius

rows, cols = [], []
dx = 3/2 * radius
dy = np.sqrt(3) * radius
y = y_min

row_idx = 0
while y < y_max:
    offset = (row_idx % 2) * (radius * 0.75)
    x = x_min + offset
    while x < x_max:
        cols.append(x); rows.append(y)
        x += dx
    y += dy
    row_idx += 1

pd.DataFrame({"x": cols, "y": rows}).to_csv("data/hex_layout_baseline.csv", index=False)
print("✅ Hexagonal baseline layout generated.")
