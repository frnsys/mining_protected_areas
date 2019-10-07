import os
import json
import fiona
from tqdm import tqdm
from sat import Satellite
from shapely.geometry import shape
from collections import defaultdict

MINING_SHAPEFILE = '../data/concessions/Mining_concessions.shp'
PROTECTED_SHAPEFILE = '../data/protected/WDPA_poly_Sep2019.shp'

def filter_feat(feat, countries):
    iso = feat['properties']['PARENT_ISO']
    marine = feat['properties']['MARINE']
    return iso in countries and marine != '2'

# Filter to protected features in countries
# we have mining concession data for
if not os.path.exists('data/protected.json'):
    countries = set()
    mining = list(fiona.open(MINING_SHAPEFILE))
    for feat in tqdm(mining, total=len(mining), desc='Getting concession countries'):
        iso = feat['properties']['country']
        countries.add(iso)

    feats = fiona.open(PROTECTED_SHAPEFILE)
    feats = [f for f in feats if filter_feat(f, countries)]
    with open('data/protected.json', 'w') as f:
        json.dump(feats, f)
else:
    with open('data/protected.json', 'r') as f:
        feats = json.load(f)

feats_by_country = defaultdict(list)
for feat in feats:
    iso = feat['properties']['PARENT_ISO']
    feats_by_country[iso].append(feat)

meta = {}
for iso, fs in tqdm(feats_by_country.items(), 'Calculating regions'):
    bounds = [float('inf'), float('inf'), -float('inf'), -float('inf')]
    for f in fs:
        shp = shape(f['geometry'])
        xmin, ymin, xmax, ymax = shp.bounds
        if xmin < bounds[0]:
            bounds[0] = xmin
        if ymin < bounds[1]:
            bounds[1] = ymin
        if xmax > bounds[2]:
            bounds[2] = xmax
        if ymax > bounds[3]:
            bounds[3] = ymax

    xmin, ymin, xmax, ymax = bounds
    box = [
        [xmin, ymin],
        [xmax, ymin],
        [xmax, ymax],
        [xmin, ymax]
    ]

    meta[iso] = {
        'box': box,
        'bounds': bounds,
        'feats': [f['id'] for f in fs]
    }

with open('data/regions.json', 'w') as f:
    json.dump(meta, f)

sat = Satellite()
scale = 200
for iso, m in tqdm(meta.items(), desc='Creating export tasks'):
    feat = {
        'id': 'REGION_{}_{}'.format(iso, scale),
        'type': 'Feature',
        'geometry': {
            'type': 'Polygon',
            'coordinates': [m['box']]
        }
    }

    # https://developers.google.com/earth-engine/scale
    sat.export_image_to_drive(feat, folder='protected_areas', max_pixels=4e9, scale=scale)
