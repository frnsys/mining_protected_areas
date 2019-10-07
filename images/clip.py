import os
import math
import json
import fiona
import transform
import numpy as np
from tqdm import tqdm
from collections import defaultdict
from shapely import affinity
from shapely.geometry import shape, mapping
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

DEBUG = True
# Image.MAX_IMAGE_PIXELS = None # To avoid DecompressionBombError

font = ImageFont.truetype('fonts/FantasqueSansMono-RegItalic.ttf', size=64)

feats = {}
feats_by_country = defaultdict(list)
with open('data/protected.json', 'r') as f:
    for feat in json.load(f):
        feats[feat['id']] = feat
        iso = feat['properties']['PARENT_ISO']
        feats_by_country[iso].append(feat['id'])

regions_by_feat = {}
with open('data/regions.json', 'r') as f:
    regions = json.load(f)
    for r_id, region in regions.items():
        for f_id in region['feats']:
            regions_by_feat[f_id] = r_id

# Check that all countries are constrained to one region
regions_by_country = {}
for iso, f_ids in feats_by_country.items():
    # One or two times a feature is absent. Not sure why, but it's
    # infrequent enough that it's not a high priority
    rs = [regions_by_feat[f_id] for f_id in f_ids if f_id in regions_by_feat]
    rs = list(set(rs))
    try:
        assert len(rs) == 1
    except:
        print('ASSERTION FAILURE FOR {}, REGIONS: {}'.format(iso, rs))
        continue # Just skip
    regions_by_country[iso] = rs[0]


MINING_SHAPEFILE = '../data/concessions/Mining_concessions.shp'
concessions_by_country = defaultdict(list)
for feat in tqdm(fiona.open(MINING_SHAPEFILE), desc='Concessions'):
    iso = feat['properties']['country']
    concessions_by_country[iso].append(feat)

THREATENED_IDS = []
intersected = set()
with open('../data/intersections.json', 'r') as f:
    intersections = json.load(f)
    for vs in tqdm(intersections, desc='Intersections'):
        for v in vs:
            intersected.add(v)

# Protected areas, identifying threatened areas
with open('../data/protected.json', 'r') as f:
    protected = json.load(f)
for i, feat in tqdm(enumerate(protected['features']), desc='Categorizing'):
    if i in intersected:
        THREATENED_IDS.append(feat['id'])

countries = {}
country_names = {}
with open('data/countries.geojson', 'r') as f:
    for feat in json.load(f)['features']:
        iso = feat['properties']['ISO_A3']
        if iso in regions_by_country:
            countries[iso] = feat
            country_names[iso] = feat['properties']['ADMIN']

for iso, r_id in tqdm(regions_by_country.items(), desc='Countries'):
    fpath = 'data/tif/REGION_{}_200.tif'.format(r_id)
    if not os.path.exists(fpath): continue

    region = regions[r_id]

    # Get as web mercator (which the region tifs are exported as)
    _, shp = transform.from_wgs84({
        'geometry': {
            'coordinates': [region['box']],
            'type': 'Polygon'
        }
    })
    xmin, ymin, xmax, ymax = shp.bounds

    # Open source image
    try:
        region_im = Image.open(fpath).convert('RGBA')
    except Exception as e:
        print('Exception for {}: {}'.format(iso, e))
        continue

    saturation = ImageEnhance.Color(region_im)
    region_im = saturation.enhance(2)

    # Create mask image
    maskIm = Image.new('L', region_im.size, 0)
    maskDraw = ImageDraw.Draw(maskIm)

    # For whatever reason, all the other coordinates I have
    # are vertically flipped. It's easier to just flip the region image
    # and flip everything back at the end.
    region_im = region_im.transpose(Image.FLIP_TOP_BOTTOM)
    debug_im = region_im.copy()
    debug = ImageDraw.Draw(debug_im)

    # Calculate scale (from web mercator to region image size)
    width = xmax - xmin
    h_scale = region_im.width/width
    height = ymax - ymin
    v_scale = region_im.height/height

    # Translation
    translation = (xmin, ymin)

    # Keep track of overall boundaries for all protected area features
    p_bounds = [float('inf'), float('inf'), -float('inf'), -float('inf')]
    region_paths = []
    for f_id in tqdm(feats_by_country[iso], 'Features ({})'.format(iso)):
        feat = feats[f_id]
        feat, shp = transform.from_wgs84(feat)

        if shp.type == 'MultiPolygon':
            shps = list(shp)
        else:
            shps = [shp]

        # For each shape that makes up the feature
        for shp in shps:
            # Get geographic bounds
            xmin_s, ymin_s, xmax_s, ymax_s = shp.bounds

            if xmin_s < p_bounds[0]:
                p_bounds[0] = xmin_s
            if ymin_s < p_bounds[1]:
                p_bounds[1] = ymin_s
            if xmax_s > p_bounds[2]:
                p_bounds[2] = xmax_s
            if ymax_s > p_bounds[3]:
                p_bounds[3] = ymax_s

            # Adjust shape scale and position to match region
            shp_ = affinity.translate(shp, -xmin_s, -ymin_s)
            shp_ = affinity.scale(shp_, h_scale, v_scale, origin=(0,0))
            shp_ = affinity.translate(shp_, (xmin_s - translation[0]) * h_scale, (ymin_s - translation[1]) * v_scale)
            shp = shp_

            path = list(shp.exterior.coords)
            interiors = [list(intr.coords) for intr in shp.interiors]

            if DEBUG:
                debug.polygon(path, outline='red', fill='red')

            region_paths.append(path)

            # Draw onto mask image
            maskDraw.polygon(path, outline=255, fill=255)
            for int_path in interiors:
                maskDraw.polygon(int_path, outline=0, fill=0)
                if DEBUG:
                    debug.polygon(int_path, outline='blue', fill='blue')


    if DEBUG:
        debug_im.transpose(Image.FLIP_TOP_BOTTOM).save('/tmp/debug.png', optimize=True)
        maskIm.transpose(Image.FLIP_TOP_BOTTOM).save('/tmp/debug_mask.png', optimize=True)

    # Blur mask
    blurRadius = 0
    if blurRadius > 0:
        maskIm = maskIm.filter(ImageFilter.GaussianBlur(blurRadius))

    # Apply mask
    region_im_arr = np.asarray(region_im)
    mask = np.array(maskIm)
    clippedArr = np.empty(region_im_arr.shape, dtype='uint8')
    clippedArr[:,:,:3] = region_im_arr[:,:,:3]
    clippedArr[:,:,3] = mask
    pa_im = Image.fromarray(clippedArr, 'RGBA')

    pa_draw = ImageDraw.Draw(pa_im)

    # Outline protected areas
    for path in region_paths:
        if f_id in THREATENED_IDS:
            color = '#f9d225'
        else:
            color = 'green'
        pa_draw.polygon(path, outline=color)

    # Draw concessions
    for feat in tqdm(concessions_by_country[iso], 'Concessions ({})'.format(iso)):
        feat, shp = transform.from_wgs84(feat)

        if shp.type == 'MultiPolygon':
            shps = list(shp)
        else:
            shps = [shp]

        for shp in shps:
            # Adjust shape scale and position to match region
            shp_ = affinity.translate(shp, -xmin_s, -ymin_s)
            shp_ = affinity.scale(shp_, h_scale, v_scale, origin=(0,0))
            shp_ = affinity.translate(shp_, (xmin_s - translation[0]) * h_scale, (ymin_s - translation[1]) * v_scale)
            shp = shp_

            path = list(shp.exterior.coords)

            # TODO testing drawing paths
            pa_draw.polygon(path, outline='red')

    # Crop the region image to
    # just the protected areas for this country
    x = (p_bounds[0] - translation[0]) * h_scale
    y = (p_bounds[1] - translation[1]) * v_scale
    w = (p_bounds[2] - p_bounds[0]) * h_scale
    h = (p_bounds[3] - p_bounds[1]) * v_scale
    crop = [x, y, x + w, y + h]
    pa_im = pa_im.crop(crop)

    if DEBUG:
        pa_im.transpose(Image.FLIP_TOP_BOTTOM).save('/tmp/debug_pa.png', optimize=True)

    c_feat = countries[iso]
    _, c_shp = transform.from_wgs84(c_feat)
    c_bounds = c_shp.bounds

    # The boundaries of the country geojson
    # and protected areas might be different,
    # get bounds that encompass both
    xmin = min(p_bounds[0], c_bounds[0])
    ymin = min(p_bounds[1], c_bounds[1])
    xmax = max(p_bounds[2], c_bounds[2])
    ymax = max(p_bounds[3], c_bounds[3])

    # Calculate width and height for composite image
    width, height = math.ceil((xmax - xmin)*h_scale), math.ceil((ymax - ymin)*v_scale)
    im = Image.new('RGBA', (width, height), (255,255,255,0))

    # Transform country shape for composite image
    c_shp = affinity.translate(c_shp, -c_bounds[0], -c_bounds[1])
    c_shp = affinity.scale(c_shp, h_scale, v_scale, origin=(0,0))
    c_shp = affinity.translate(c_shp, (c_bounds[0] - xmin) * h_scale, (c_bounds[1] - ymin) * v_scale)

    # Draw country outline
    paths = []
    if c_shp.type == 'MultiPolygon':
        paths = [list(s.exterior.coords) for s in c_shp]
    else:
        paths = [list(c_shp.exterior.coords)]

    draw = ImageDraw.Draw(im)
    for path in paths:
        draw.polygon(path, outline='#3783fc')
        # if DEBUG:
        #     draw.polygon(path, fill='wheat')

    tmp_im = Image.new('RGBA', (width, height), (255,255,255,0))
    tmp_im_arr = np.array(tmp_im)
    x = int((p_bounds[0] - xmin) * h_scale)
    y = int((p_bounds[1] - ymin) * v_scale)
    pa_im_arr = np.array(pa_im)
    h, w, _ = pa_im_arr.shape
    tmp_im_arr[y:y+h, x:x+w, :] = pa_im_arr
    pa_im = Image.fromarray(tmp_im_arr, 'RGBA')
    im = Image.alpha_composite(pa_im, im)

    # Background
    bg_color = (12,12,12,255)
    bg_im = Image.new('RGBA', (width, height), bg_color)
    im = Image.alpha_composite(bg_im, im)

    out = im.transpose(Image.FLIP_TOP_BOTTOM)

    draw = ImageDraw.Draw(out)
    draw.text((50, out.height - 120), country_names[iso], font=font, fill=(255,255,255,255))

    out.save('data/img/{}.png'.format(iso), optimize=True)
    out.convert('RGB').save('data/img/{}.jpg'.format(iso), optimize=True, quality=75)
