"""
Simple python programm to get elevation
from Open Topo Data
(C) Kilian Eisenegger 2025
"""
import requests

API_URL = "https://api.opentopodata.org/v1/aster30m"
coords = [
    [46.5776, 8.0059],   # Eiger
    [46.5586, 7.9856],   # Mönch
    [46.5475, 7.9625],   # Jungfrau
]

# Transform coordinates in "lat,lon|lat,lon|..."
locations = "|".join([f"{lat},{lon}" for lat, lon in coords])

# Send request
response = requests.get(API_URL, params={"locations": locations})
data = response.json()

# Compile results
result = []
for coord, res in zip(coords, data["results"]):
    lat, lon = coord
    elev = res.get("elevation")
    result.append([lat, lon, elev])
    print(f"{lat}, {lon} → {elev:.1f} m")

