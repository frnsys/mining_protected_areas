import json
from tqdm import tqdm
from transform import to_wgs84

intersected = set()
with open('data/intersections.json', 'r') as f:
    intersections = json.load(f)
    for vs in tqdm(intersections, desc='Intersections'):
        for v in vs:
            intersected.add(v)

# Protected areas, separating overlapped and non-overlapped
with open('data/protected.json', 'r') as f:
    protected = json.load(f)

pa = {
    'overlap': {'type': 'FeatureCollection', 'features': []},
    'no_overlap': {'type': 'FeatureCollection', 'features': []}
}
for i, feat in tqdm(enumerate(protected['features']), desc='Separating protected areas'):
    k = 'overlap' if i in intersected else 'no_overlap'
    feat, shp = to_wgs84(feat)
    pa[k]['features'].append(feat)
for k, d in pa.items():
    with open('data/tile/protected_{}.json'.format(k), 'w') as f:
        json.dump(d, f)

with open('data/concessions.json', 'r') as f:
    concessions = json.load(f)
concessions['features'] = [to_wgs84(feat)[0] for feat in concessions['features']]
with open('data/tile/concessions.json', 'w') as f:
    json.dump(concessions, f)