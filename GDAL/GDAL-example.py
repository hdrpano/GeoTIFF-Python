"""
Simple GDAL programm to get elevation
(C) Kilian Eisenegger 2025
"""
from osgeo import gdal
import numpy as np
gdal.UseExceptions()

def get_elevation(lat, lon, dataset):
    """Get elevation im m from GeoTIFF for lat/lon"""
    gt = dataset.GetGeoTransform()
    inv_gt = gdal.InvGeoTransform(gt)
    px, py = gdal.ApplyGeoTransform(inv_gt, lon, lat)
    
    px, py = int(px), int(py)
    band = dataset.GetRasterBand(1)
    data = band.ReadAsArray(px, py, 1, 1)
    
    if data is None:
        return None
    return float(data[0,0])

if __name__ == "__main__":
    # Load ASTER DEM 
    dem_path = "dem_aster.tif"
    ds = gdal.Open(dem_path)

    coords = [
        [46.5776, 8.0059],   # Eiger
        [46.5586, 7.9856],   # Mönch
        [46.5475, 7.9625],   # Jungfrau
    ]

    for lat, lon in coords:
        h = get_elevation(lat, lon, ds)
        print(f"{lat}, {lon} → {h:.1f} m")
