import camelot
import pandas as pd
from pathlib import Path

pdf = Path("data/5G_Towers_in_Manila.pdf")
out = Path("data/manila_towers_clean.csv")

print("Reading PDF with Camelot… this may take a minute")

# Try reading all pages
tables = camelot.read_pdf(str(pdf), pages='all', flavor='stream')  # or 'lattice' if table lines are visible
print(f"Found {tables.n} tables in the PDF")

# Combine all extracted tables
df_all = pd.concat([t.df for t in tables], ignore_index=True)

# Clean column names safely (ignore non-string headers)
df_all.columns = [
    str(c).strip().lower().replace(" ", "_") if isinstance(c, str) else f"col_{i}"
    for i, c in enumerate(df_all.columns)
]


# Save
df_all.to_csv(out, index=False)
print("Saved clean CSV to", out)
