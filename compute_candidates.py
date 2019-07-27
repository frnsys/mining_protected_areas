import json
import fiona
import pandas as pd
from tqdm import tqdm
from pyqtree import Index
from transform import from_wgs84

MINING_SHAPEFILE = 'data/concessions/Mining_concessions.shp'
PROTECTED_SHAPEFILE = 'data/protected/WDPA_Jun2019-shapefile-polygons.shp'

def to_json(props, feats, out):
    print('Saving...')
    df = pd.DataFrame(props)
    df.to_csv('data/{}_props.csv'.format(out), index=False)

    with open('data/{}.json'.format(out), 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': feats}, f)
    print('Saved', out)

# Compute countries with concession data
# And save concession shapefile as geojson
countries = set()
props, feats = [], []
mining = list(fiona.open(MINING_SHAPEFILE))
for i, shp in tqdm(enumerate(mining), total=len(mining), desc='Concessions'):
    iso = shp['properties']['country']
    countries.add(iso)

    props.append(shp['properties'])
    feats.append(shp)
to_json(props, feats, 'concessions')

print('Countries:', countries)
with open('data/countries.json', 'w') as f:
    json.dump(list(countries), f)

# Compute overall bounds,
# and convert to geojson,
# keeping only shapes in the countries of interest
bounds = [None, None, None, None]
protected = []
props, feats = [], []
for feat in tqdm(fiona.open(PROTECTED_SHAPEFILE), desc='Computing bounds'):
    iso = feat['properties']['PARENT_ISO']
    marine = feat['properties']['MARINE']
    if iso not in countries or marine == '2': continue

    feat, shp = from_wgs84(feat)
    props.append(feat['properties'])
    feats.append(feat)

    shp_bounds = shp.bounds
    for i, (b, B) in enumerate(zip(shp_bounds, bounds)):
        if B is None or (i < 2 and b < B) or (i >= 2 and b > B):
            bounds[i] = b
    protected.append(shp)
to_json(props, feats, 'protected')

# Create Q-tree
idx = Index(bbox=bounds)
shapes = {}
for i, shp in enumerate(tqdm(protected, desc='Indexing protected areas')):
    idx.insert(i, shp.bounds)
    shapes[i] = shp

# Compute bounding box intersections with mining concessions
# and save to geojson
props, feats = [], []
intersects, n_matches = {}, []
mining = list(fiona.open(MINING_SHAPEFILE))
for i, feat in tqdm(enumerate(mining), total=len(mining), desc='Computing concession overlap candidates'):
    feat, shp = from_wgs84(feat)
    props.append(feat['properties'])
    feats.append(feat)

    matches = idx.intersect(shp.bounds)
    if matches:
        intersects[i] = matches
        n_matches.append(len(matches))
to_json(props, feats, 'concessions')

with open('data/intersection_candidates.json', 'w') as f:
    json.dump(intersects, f)