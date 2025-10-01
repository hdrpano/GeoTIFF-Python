![Python 3.13](https://img.shields.io/badge/Python-3.13-green.svg)
![GDAL 3.11.1](https://img.shields.io/badge/GDAL-3.11.1-green.svg)
![license MIT](https://img.shields.io/badge/license-MIT-green.svg) 
#Python GeoTIFF's with Open Topo Date or GDAL

In this repository, you will find Python programmes that allow you to retrieve precise elevation data from GEOTIFF files using Open Topo Data or GDAL for Python.
The WGS84 and LV95 (Switzerland) formats are supported. You will learn how to install a local server for OPEN TOPO DATA and how to install GDAL for Python.

The [map-creator](https://apps.apple.com/us/app/map-creator/id1549471927) uses GeoTIFF's to create terrain follow AGL missons. 
![map-creator AGL](https://map-creator.com/index_htm_files/444.jpg)
![map-creator AGL](images/map-creator.png)
##Elevation with Open Topo Data
###Open Topo Data Server

[Open Topo Data](https://www.opentopodata.org/) is a REST API server for your elevation data. It is open source. 

`https://api.opentopodata.org/v1/aster30m?locations=46.5776,8.0059|46.5586,7.9856|46.5475,7.9625`

```Json
{
  "results": [
    {
      "dataset": "aster30m",
      "elevation": 3876.0,
      "location": {
        "lat": 46.5776,
        "lng": 8.0059
      }
    },
    {
      "dataset": "aster30m",
      "elevation": 3331.0,
      "location": {
        "lat": 46.5586,
        "lng": 7.9856
      }
    },
    {
      "dataset": "aster30m",
      "elevation": 3375.0,
      "location": {
        "lat": 46.5475,
        "lng": 7.9625
      }
    }
  ],
  "status": "OK"
}
```
With this small Python program you get access to Open Topoe Data. The Json response will be translated into an Array `[[lat, lon, elev]]`
```Python
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
```
You get this response.
```Console
46.5776, 8.0059 → 3876.0 m
46.5586, 7.9856 → 3331.0 m
46.5475, 7.9625 → 3375.0 m
``` 
##Install Open Topo Data on Windows 11
The easiest way to run Open Topo Data is with Docker.

Get [docker](https://docs.docker.com/desktop/setup/install/windows-install/) for Windows.
You need [git](https://git-scm.com/downloads/win) for Windows too.
```Console
git clone https://github.com/ajnisbet/opentopodata.git
cd opentopodata
```
I modified the Dockerfile for Windows. Replace the Dockerfile from the repository with tis one. 

```Console
FROM python:3.11.10-slim-bookworm as builder
# Add modifiction for Windows 11
RUN set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        libpcre3-dev \
        gcc \
        g++ \
        make \
        && rm -rf /var/lib/apt/lists/*
# Container for packages that need to be built from source but have massive dev dependencies.
RUN set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3.11-dev

RUN pip config set global.disable-pip-version-check true && \
    pip wheel --wheel-dir=/root/wheels uwsgi==2.0.28 && \
    pip wheel --wheel-dir=/root/wheels regex==2024.11.6 

# The actual container.
FROM python:3.11.10-slim-bookworm
RUN set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        inotify-tools \
        nano \
        nginx \
        memcached \
        supervisor && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/wheels /root/wheels
COPY requirements.txt /app/requirements.txt
RUN pip install \
        --no-index \
        --no-cache-dir \
        --disable-pip-version-check \
        --find-links=/root/wheels \
        uwsgi regex && \
    pip install --no-cache-dir --disable-pip-version-check --default-timeout=1000 -r /app/requirements.txt && \
        rm -rf /root/.cache/pip/* && \
        rm root/wheels/* && \
        rm /app/requirements.txt

WORKDIR /app
COPY . /app/

RUN echo > /etc/nginx/sites-available/default && \
    cp /app/docker/nginx.conf /etc/nginx/conf.d/nginx.conf && \
    cp /app/docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["sh", "/app/docker/run.sh"]
EXPOSE 5000

ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV GDAL_DISABLE_READDIR_ON_OPEN=TRUE
ENV GDAL_NUM_THREADS=ALL_CPUS
ENV GDAL_CACHEMAX=512
```
We have to edit the `config.yaml` file to put in our dataset.
```Console
max_locations_per_request: 100 
access_control_allow_origin: '*'
datasets:
- name: aster30m
  path: data/aster30m/
```
Now we need a dataset. We will use ASTER from the NASA. ASTER GDEM is a 1 arc-second resolution, corresponding to a resolution of about 30m at the equator. Coverage is provided from from -83 to 83 degrees latitude. This dataset has 22'912 tiles. We will only download tiles for our region. I build a python program to make this easy.

[Select Aster tiles](./images/ASTER-tiles.png). Use this python program `Download-Aster-GeoTiff.py` from this repository. The program will unzip the GeoTIFF files and remove all ^*num.tif'  files. Copy your GeoTIFF files into `/your path/opentopodata/data/aster30m`



Now you can run the build.
```Console
docker build --tag opentopodata --file docker/Dockerfile .
```



```console
uname -m
brew update
brew install gdal
gdalinfo -–version
pip install GDAL=version
```
```bat
dir
```


Das ist **Fett**

Das ist *Italic*

Das ist Code: `let a = 1`

---

Das ist ein [hdrpano](https://hdrpano.ch)

![map-creator AGL](https://map-creator.com/index_htm_files/444.jpg)

<center><iframe width="560" height="315" src="https://www.youtube.com/embed/ZRGM7KerPKU" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></center>

[![Watch the video](https://img.youtube.com/vi/ZRGM7KerPKU/maxresdefault.jpg)](https://youtu.be/ZRGM7KerPKU)

Text
```console
Fine DEM (0.5m): (2000, 2000)
Coarse DEM (2m): (500, 500) 
Scalefactor: x=4.00, y=4.00 
nearest  → RMSE=0.523, MAE=0.329 
bilinear → RMSE=0.397, MAE=0.243  
cubic    → RMSE=0.396, MAE=0.242 
```

```js
Func Test()
    frameborder()
```

```python
methods = {
    "nearest": 0,
    "bilinear": 1,
    "cubic": 3
}
```

##Windows 11 GDAL Python Installation
Instead of building GDAL yourself, you can install ready-made wheels:
Find the right version of Python and GDAL that work together. → List of compatible versions (unofficial but very reliable Windows builds by Christoph Gohlke).
[GDAL wheels Windows 11](https://github.com/cgohlke/geospatial-wheels/releases/tag/v2025.7.4)

```python --version```

Download the .whl for your Python version `(e.g. GDAL-3.7.2-cp311-cp311-win_amd64.whl for Python 3.11, 64-bit).`

Install it manually:

```console
pip install path\to\GDAL-3.7.2-cp311-cp311-win_amd64.whl
```

Important: The Python version and architecture (32/64-bit) must match exactly!

##Mac OS GDAL Python installation
Use the correct brew for Mac Silicon or Intel. The terminal must not use Rosetta on Mac Silicon. 

```console
uname -m
brew update
brew install gdal
gdalinfo -–version
pip install GDAL==version
```
###Homebrew uses /opt/homebrew/Cellar/gdal/<version>/ on Mac Silicon.

```console
/opt/homebrew/bin/      → z.B. gdalinfo, ogr2ogr, gdal_translate
/opt/homebrew/lib/      → z.B. libgdal.dylib
/opt/homebrew/include/  → Header-Dateien
/opt/homebrew/share/    → Daten und Formate
```

###Intel Homebrew
```console
local/Cellar/gdal/<version>/
/usr/local/bin/
/usr/local/lib/
```