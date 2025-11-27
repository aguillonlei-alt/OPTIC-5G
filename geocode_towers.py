import pandas as pd
from geopy.geocoders import Nominatim
from time import sleep
from pathlib import Path

input_file = Path("..data/manila_towers_clean.csv")
output_file = Path("..data/manila_towers_geocoded.csv")

# Read tower list 
df = pd.read_csv(input_file, names=["text"], skip_blank_lines=True)

# Find rows with the key words under the address column
addresses = df[df["address"].str.contains("Barangay|Street|St|Manila|District", case=False, na=False)].reset_index(drop=True)
print(f"Found {len(addresses)} possible tower addresses.")

geolocator = Nominatim(user_agent="optic5g-geocoder")
results = []

# Find the lat. long. of the address
for i, row in addresses.iterrows():
    addr = row["text"]
    try:
        location = geolocator.geocode(addr + ", Philippines", timeout=5)
        if location:
            results.append({
                "address": addr,
                "latitude": location.latitude,
                "longitude": location.longitude
            })
            print(f"{i+1}/{len(addresses)} {addr} → ({location.latitude:.4f}, {location.longitude:.4f})")
        else:
            print(f"{i+1}/{len(addresses)} {addr} → not found")
    except Exception as e:
        print(f"Error on {addr}: {e}")
    sleep(1)

pd.DataFrame(results).to_csv(output_file, index=False)
print(f"\n Saved geocoded file: {output_file}")
