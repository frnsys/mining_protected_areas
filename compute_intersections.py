import fiona
import numpy as np
from tqdm import tqdm
from pyqtree import Index
from shapely.geometry import shape

PROTECTED_SHAPEFILE = 'data/protected/WDPA_Jun2019-shapefile-polygons.shp'
CONCESSIONS_SHAPEFILE = 'data/concessions/Mining_concessions.shp'

# Compute overall bounds
bounds = [None, None, None, None]
for shp in tqdm(fiona.open(PROTECTED_SHAPEFILE), desc='Computing bounds'):
    shp = shape(shp['geometry'])
    for i, (b, B) in enumerate(zip(shp.bounds, bounds)):
        if B is None or (i < 2 and b < B) or (i >= 2 and b > B):
            bounds[i] = b

# Create Q-tree
idx = Index(bbox=bounds)
for i, shp in enumerate(tqdm(fiona.open(PROTECTED_SHAPEFILE), desc='Indexing protected areas')):
    if shp['properties']['MARINE'] == '2': continue
    shp = shape(shp['geometry'])
    idx.insert(i, shp.bounds)

# Compute intersections with mining concessions
intersects, n_matches = [], []
concessions = list(fiona.open(CONCESSIONS_SHAPEFILE))
for i, shp in tqdm(enumerate(concessions), desc='Computing concession overlaps'):
    shp = shape(shp['geometry'])
    matches = idx.intersect(shp.bounds)
    if matches:
        intersects.append((i, matches))
        n_matches.append(len(matches))

print('p concessions intersecting w/ at least one protected area:', len(intersects)/len(concessions))
print('mean intersections w/ protected areas:', np.mean(n_matches))