# Open Topo Date Aster local Server
# Download ASTER 30m for a specific country
# The Aster files are 1° tiles
# Unzip so that only GeoTiffs remain
# Kilian Eisenegger 2025

import os
import re
import requests
import zipfile

# URL with all ASTER GDEM V3 download links
URL_LIST = "https://www.opentopodata.org/datasets/aster30m_urls.txt"

# Bounding Box Switzerland
LAT_MIN, LAT_MAX = 45, 47
LON_MIN, LON_MAX = 5, 11

# 1° buffer in all directions
LAT_MIN -= 1
LAT_MAX += 1
LON_MIN -= 1
LON_MAX += 1

# Destination folder
OUTDIR = "aster_swiss_tiles"
os.makedirs(OUTDIR, exist_ok=True)

# Download the complete URL list
resp = requests.get(URL_LIST)
resp.raise_for_status()
urls = resp.text.splitlines()

def parse_tile_name(url):
    match = re.search(r'N(\d{2})E(\d{3})', url)
    if match:
        lat = int(match.group(1))
        lon = int(match.group(2))
        return lat, lon
    return None, None

# Filter only the relevant tiles (Switzerland + buffer)
swiss_urls = []
for url in urls:
    lat, lon = parse_tile_name(url)
    if lat is None:
        continue
    if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
        swiss_urls.append(url)

print(f"{len(swiss_urls)} Tiles found (incl. buffer).")

# Session that automatically uses .netrc
session = requests.Session()
session.headers.update({"User-Agent": "aster-downloader"})

for url in swiss_urls:
    filename = url.split("/")[-1]
    zip_path = os.path.join(OUTDIR, filename)

    tif_name = filename.replace(".zip", ".tif")
    tif_path = os.path.join(OUTDIR, tif_name)
    if os.path.exists(tif_path):
        print(f"✅ Already available: {tif_name}")
        continue

    print(f"⬇️ Lade {filename} ...")
    r = session.get(url, stream=True)
    if r.status_code == 401:
        raise Exception("❌ Unauthorized: Please check your ~/.netrc file and whether the account on urs.earthdata.nasa.gov is active.")
    r.raise_for_status()

    with open(zip_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"📦 Unpack {filename} ...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(OUTDIR)

    os.remove(zip_path)
    print(f"🗑️ ZIP removed: {filename}")

print("🎉 All GeoTIFFs for Switzerland + 1° buffer are ready!")


