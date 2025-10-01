# Open Topo Data Aster 30m
# Read KML, replace Altitude with AGL, save KML
# Work with array [[lat, lon, alt]]

import requests
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

API_URL = "https://api.opentopodata.org/v1/aster30m"
# API_URL = "http://localhost:5100/v1/aster30m"
BATCH_SIZE = 100
SLEEP_SEC = 1.1


def read_kml(filepath, logf):
    """Read KML and return coordinates as a list [lat, lon, alt]"""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except Exception as e:
        logf.write(f"[ERROR] KML lesen fehlgeschlagen: {e}\n")
        sys.exit(1)

    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    coords = []
    for coord in root.findall(".//kml:coordinates", ns):
        raw = coord.text.strip().split()
        for c in raw:
            lon, lat, alt = map(float, c.split(","))
            coords.append([lat, lon, alt])

    return coords, tree, ns


def fetch_elevations(coords, logf):
    """Get elevation values from OpenTopoData for a list of [lat, lon, alt"""
    updated = []
    for i in range(0, len(coords), BATCH_SIZE):
        batch = coords[i:i + BATCH_SIZE]

        # Query-String bauen: "lat,lon%7Clat,lon..."
        loc_str = "%7C".join(f"{lat},{lon}" for lat, lon, _ in batch)
        url = f"{API_URL}?locations={loc_str}"

        logf.write(f"[INFO] Hole Höhen für Batch {i//BATCH_SIZE+1} von {len(coords)//BATCH_SIZE+1}: {url}\n")

        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logf.write(f"[ERROR] Request failed: {e}\n")
            sys.exit(1)

        results = data.get("results", [])
        for (lat, lon, _), res in zip(batch, results):
            elev = res.get("elevation", 0)
            updated.append([lat, lon, elev])

        time.sleep(SLEEP_SEC)

    return updated


def write_kml(coords, tree, ns, output_file, logf):
    """Overwrite KML with new heights"""
    idx = 0
    for coord_elem in tree.findall(".//kml:coordinates", ns):
        raw = coord_elem.text.strip().split()
        new_coords = []
        for _ in raw:
            lat, lon, alt = coords[idx]
            new_coords.append(f"{lon},{lat},{alt}")
            idx += 1
        coord_elem.text = " ".join(new_coords)

    try:
        tree.write(output_file, encoding="utf-8", xml_declaration=True)
        logf.write(f"[INFO] File saved: {output_file}\n")
    except Exception as e:
        logf.write(f"[ERROR] Failed to save: {e}\n")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python topo_kml.py input.kml output.kml log.txt")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    log_file = Path(sys.argv[3])

    with open(log_file, "w", encoding="utf-8") as logf:
        logf.write("[START] OpenTopoData KML elevation query\n")

        coords, tree, ns = read_kml(input_file, logf)
        logf.write(f"[INFO] {len(coords)} Waypoints found\n")

        new_coords = fetch_elevations(coords, logf)
        write_kml(new_coords, tree, ns, output_file, logf)

        logf.write("[END] Processing completed\n")

    print(f"Done! Result in {output_file}, Log in {log_file}")
