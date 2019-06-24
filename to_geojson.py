import json
import fiona
import pandas as pd
from tqdm import tqdm

data = [
    ('data/protected/WDPA_Jun2019-shapefile-polygons.shp', 'protected')
    ('data/concessions/Mining_concessions.shp', 'concessions')
]

for inp, out in data:
    props = []
    features = []
    for shp in tqdm(fiona.open(inp)):
        props.append(shp['properties'])
        features.append(shp)

    df = pd.DataFrame(props)
    df.to_csv('data/{}_props.csv'.format(out), index=False)

    with open('data/{}.json'.format(out), 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': features}, f)