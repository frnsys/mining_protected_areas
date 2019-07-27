import pyproj
from functools import partial
from shapely.ops import transform
from shapely.geometry import shape, mapping

# Note: x, y = lng, lat
wgs84 = pyproj.Proj({'init':'epsg:4326'}, preserve_units=True)
web_mercator = pyproj.Proj({'init': 'epsg:3857'}, preserve_units=True)
from_proj = partial(pyproj.transform, wgs84, web_mercator)
to_proj = partial(pyproj.transform, web_mercator, wgs84)

def from_wgs84(feat):
    shp = transform(from_proj, shape(feat['geometry']))
    feat['geometry'] = mapping(shp)
    return feat, shp

def to_wgs84(feat):
    shp = transform(to_proj, shape(feat['geometry']))
    feat['geometry'] = mapping(shp)
    return feat, shp
