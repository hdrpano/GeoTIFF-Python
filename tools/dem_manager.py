"""
This Python class reads coordinates and supplements the elevation with locally stored GeoTIFF files.
The formats WGS84 and LV95 (Switzerland) are supported. For LV95, 0.5 m is automatically used if available.
The files are pre-sorted by file name and only loaded if they correspond to the waypoints being searched for.
If no exact GeoTIFFs are found, the class uses ASTER 30m GeoTIFFs. (Fallback)
The GeoTIFF files must be in their original format and must not be renamed.

(C) Kilian Eisenegger 2025
"""
from pathlib import Path
from osgeo import gdal, osr
import re
import math

gdal.UseExceptions()

class DEMTile:
    """Single DEM GeoTIFF with WGS84 BBox, transformation and elevation query"""
    def __init__(self, path, epsilon_deg=1e-6):
        self.path = str(path)
        self.ds = gdal.Open(self.path)
        if not self.ds:
            raise RuntimeError(f"Unable to open GeoTIFF: {self.path}")

        self.gt = self.ds.GetGeoTransform()
        self.rx = self.ds.RasterXSize
        self.ry = self.ds.RasterYSize

        self.proj = osr.SpatialReference(wkt=self.ds.GetProjection())
        self.proj.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        self.wgs84 = osr.SpatialReference()
        self.wgs84.ImportFromEPSG(4326)
        self.wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        try:
            self.epsg = int(self.proj.GetAttrValue("AUTHORITY", 1))
        except Exception:
            self.epsg = None

        self.need_transform = (self.epsg not in (None, 4326))
        if self.need_transform:
            self.to_dem = osr.CoordinateTransformation(self.wgs84, self.proj)
            self.to_wgs84 = osr.CoordinateTransformation(self.proj, self.wgs84)
        else:
            self.to_dem = None
            self.to_wgs84 = None

        # Grid corners in WGS84
        x0, px_w, rot_x, y0, rot_y, px_h = self.gt
        corners = [
            (x0, y0),
            (x0 + self.rx*px_w, y0),
            (x0, y0 + self.ry*px_h),
            (x0 + self.rx*px_w, y0 + self.ry*px_h),
        ]
        if self.need_transform:
            corners_wgs = [self.to_wgs84.TransformPoint(cx, cy) for cx, cy in corners]
        else:
            corners_wgs = [(cx, cy, 0) for cx, cy in corners]

        lons = [c[0] for c in corners_wgs]
        lats = [c[1] for c in corners_wgs]
        self.minlon = min(lons) - epsilon_deg
        self.maxlon = max(lons) + epsilon_deg
        self.minlat = min(lats) - epsilon_deg
        self.maxlat = max(lats) + epsilon_deg

        band = self.ds.GetRasterBand(1)
        self.nodata = band.GetNoDataValue()

    def bbox_contains(self, lat, lon):
        return (self.minlat <= lat <= self.maxlat) and (self.minlon <= lon <= self.maxlon)

    def get_elevation(self, lat, lon):
        if self.need_transform:
            x, y, _ = self.to_dem.TransformPoint(lon, lat)
        else:
            x, y = lon, lat

        px_f = (x - self.gt[0]) / self.gt[1]
        py_f = (y - self.gt[3]) / self.gt[5]
        px = int(math.floor(px_f + 0.5))
        py = int(math.floor(py_f + 0.5))

        if not (0 <= px < self.rx and 0 <= py < self.ry):
            return None

        band = self.ds.GetRasterBand(1)
        val = band.ReadAsArray(px, py, 1, 1)
        if val is None:
            return None
        z = float(val[0, 0])
        if self.nodata is not None and z == self.nodata:
            return None
        return z


class DEMManager:
    """Manager for DEM tiles and elevation queries"""
    def __init__(self, dem_folder):
        self.dem_folder = Path(dem_folder)
        self.tiles = []

    def load_tiles_for_coords(self, coords):
        """Only loads the relevant tiles for the given points"""
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        minlat, maxlat = min(lats), max(lats)
        minlon, maxlon = min(lons), max(lons)

        tif_files = list(self.dem_folder.glob("*.tif"))

        # Recognising Swisstopo tiles
        swiss_groups = {}
        aster_tiles = []

        for path in tif_files:
            info_swiss = self._parse_swisstopo_name(path.name)
            if info_swiss:
                key = (info_swiss["ix"], info_swiss["iy"])
                swiss_groups.setdefault(key, []).append((info_swiss["res"], path))
                continue

            info_aster = self._parse_aster_name(path.name)
            if info_aster:
                info_aster["path"] = path
                aster_tiles.append(info_aster)

        chosen_paths = []

        # Select the finest Swisstopo tiles
        for key, entries in swiss_groups.items():
            entries.sort(key=lambda x: x[0])  # 0.5 < 2
            finest_path = entries[0][1]
            t = DEMTile(finest_path)
            if not (t.maxlat < minlat or t.minlat > maxlat or
                    t.maxlon < minlon or t.minlon > maxlon):
                chosen_paths.append(finest_path)

        # If no tiles, load ASTER
        if not chosen_paths:
            for info in aster_tiles:
                if not (info["maxlat"] < minlat or info["minlat"] > maxlat or
                        info["maxlon"] < minlon or info["minlon"] > maxlon):
                    chosen_paths.append(info["path"])

        self.tiles = [DEMTile(p) for p in chosen_paths]
        return self.tiles  # zurückgeben für Leaflet

    def get_elevation(self, lat, lon):
        """Query height for lat/lon"""
        for t in self.tiles:
            if t.bbox_contains(lat, lon):
                elev = t.get_elevation(lat, lon)
                if elev is not None:
                    return elev
        return None

    # -----------------------
    # Intern helpers
    # -----------------------
    def _parse_swisstopo_name(self, name):
        m = re.match(r".*?_(\d+)-(\d+)_([\d\.]+)_\d+_\d+\.tif$", name)
        if not m:
            return None
        ix = int(m.group(1))
        iy = int(m.group(2))
        res = float(m.group(3))
        return {"type": "swiss", "ix": ix, "iy": iy, "res": res}

    def _parse_aster_name(self, name):
        m = re.match(r"ASTGTMV\d+_N(\d+)E(\d+)_dem\.tif$", name)
        if not m:
            return None
        lat = int(m.group(1))
        lon = int(m.group(2))
        return {"type": "aster", "minlat": lat, "maxlat": lat+1,
                "minlon": lon, "maxlon": lon+1, "res": 30.0}


