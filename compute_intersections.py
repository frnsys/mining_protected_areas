import fiona
import pyproj
import numpy as np
from tqdm import tqdm
from shapely.geometry import shape
from pyqtree import Index

BOUND_RADIUS = 1e3 # meters
PROTECTED_SHAPEFILE = 'data/protected/WDPA_Jun2019-shapefile-polygons.shp'
MINING_SHAPEFILE = 'data/concessions/Mining_concessions.shp'

# Note: x, y = lng, lat
wgs84 = pyproj.Proj({'init':'epsg:4326'}, preserve_units=True)
web_mercator = pyproj.Proj({'init': 'epsg:3857'}, preserve_units=True)

def to_xy(bounds):
    xmin, ymin, xmax, ymax = bounds
    xmin, ymin = pyproj.transform(wgs84, web_mercator, xmin, ymin)
    xmax, ymax = pyproj.transform(wgs84, web_mercator, xmax, ymax)
    return xmin, ymin, xmax, ymax

def pad(bounds, padding):
    xmin, ymin, xmax, ymax = bounds
    return xmin-padding, ymin-padding, xmax+padding, ymax+padding

# Compute overall bounds
bounds = [None, None, None, None]
for shp in tqdm(fiona.open(PROTECTED_SHAPEFILE), desc='Computing bounds'):
    shp = shape(shp['geometry'])
    shp_bounds = pad(to_xy(shp.bounds), BOUND_RADIUS)
    for i, (b, B) in enumerate(zip(shp_bounds, bounds)):
        if B is None or (i < 2 and b < B) or (i >= 2 and b > B):
            bounds[i] = b

# Create Q-tree
idx = Index(bbox=bounds)
for i, shp in enumerate(tqdm(fiona.open(PROTECTED_SHAPEFILE), desc='Indexing protected areas')):
    shp = shape(shp['geometry'])
    shp_bounds = to_xy(shp.bounds)
    idx.insert(i, shp_bounds)

# Compute intersections with mining concessions
intersects, n_matches = [], []
mining = list(fiona.open(MINING_SHAPEFILE))
for i, shp in tqdm(enumerate(mining), total=len(mining), desc='Computing concession overlaps'):
    shp = shape(shp['geometry'])
    shp_bounds = pad(to_xy(shp.bounds), BOUND_RADIUS)
    matches = idx.intersect(shp_bounds)
    if matches:
        intersects.append((i, matches))
        n_matches.append(len(matches))

print('extending protected area radius by meters:', BOUND_RADIUS)
print('p concessions intersecting w/ at least one protected area:', len(intersects)/len(mining))
print('mean intersections w/ protected areas:', np.mean(n_matches))