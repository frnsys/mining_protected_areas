import os
import ee
from util import download_ee_image, get_bounds

def maskClouds(image):
    # Bits 3 and 5 are cloud shadow and cloud, respectively.
    cloudShadowBitMask = (1 << 3)
    cloudsBitMask = (1 << 5)

    # Get the pixel QA band.
    qa = image.select('pixel_qa')

    # Both flags should be set to zero, indicating clear conditions.
    mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0).And(qa.bitwiseAnd(cloudsBitMask).eq(0))
    return image.updateMask(mask)

ee.Initialize()
tasks = ee.data.getTaskList()

# Using Landsat 8 Surface Reflectance Tier 1
# Resolution of 30m^2
# <https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C01_T1_SR>
l8sr = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR')

# Rename band names
# (see prev link for reference)
band_names = {
    'B1': 'ultra_blue',
    'B2': 'blue',
    'B3': 'green',
    'B4': 'red',
    'B5': 'nir',
    'B6': 'swir_1',
    'B7': 'swir_2',

    # Not in this dataset
    #'B8': 'pan',
    #'B9': 'cirrus',

    'B10': 'tirs_1',
    'B11': 'tirs_2',
    'sr_aerosol': 'sr_aerosol',
    'pixel_qa': 'pixel_qa',
    'radsat_qa': 'radsat_qa'
}
old_names = ee.List(list(band_names.keys()))
new_names = ee.List(list(band_names.values()))
l8sr = l8sr.select(old_names, new_names).map(maskClouds)


class Satellite:
    def __init__(self):
        self.imgcol = l8sr

    def get_image_region(self, feat):
        """Get RGB bands for image region intersecting
        w/ this feature's geometry"""
        return self.imgcol.filter(ee.Filter.geometry(ee.Feature(feat).geometry())).median()\
            .visualize(min=0, max=3000, bands=['red', 'green', 'blue'])

    def get_image(self, feat, radius=0.02, scale=30):
        moves = [(radius, radius), (radius, -radius), (-radius, -radius), (-radius, radius)]
        feat = ee.Feature(feat)
        region = self.get_image_region(feat)
        data = feat.getInfo()

        type = data['geometry']['type']
        coords = data['geometry']['coordinates']
        if type == 'Point':
            bounds = [[coords[0]+r0, coords[1]+r1] for r0, r1 in moves]
        elif type == 'Polygon':
            bounds = coords
        else:
            xmin, ymin, xmax, ymax = get_bounds([c[0] for c in data['geometry']['coordinates']])
            bounds = [
                [xmin, ymax],
                [xmax, ymax],
                [xmax, ymin],
                [xmin, ymin]
            ]

        image = ee.Image(region)
        params = {'region': bounds, 'scale': scale}
        return image, params

    def get_images(self, feature_collection, chunk_size=10, **kwargs):
        images = []
        n_feats = feature_collection.size().getInfo()
        moves = [(radius, radius), (radius, -radius), (-radius, -radius), (-radius, radius)]

        # Process in chunks to avoid
        # exhausing EE memory
        for i in range(n_feats//chunk_size + 1):
            fs = feature_collection.toList(chunk_size, i*chunk_size)

            # Need to do this to iterate over them
            n_fs = fs.size().getInfo()

            for i in range(n_fs):
                feat = ee.Feature(fs.get(i))
                images.append(self.get_image(feat))
        return images

    def download_image(self, feat, dir='img', **kwargs):
        id = feat['id']
        impath = os.path.join(dir, '{}.png'.format(id))
        if os.path.exists(impath):
            return id, impath
        image, params = self.get_image(feat, **kwargs)
        url = image.getDownloadURL(params=params)
        impath = download_ee_image(url, id, impath)
        return id, impath

    def export_image_to_drive(self, feat, folder, max_pixels=1e8, crs='EPSG:3857', **kwargs):
        # Note: EPSG:3857 is Web Mercator
        # View tasks with `earthengine task list`
        # Exports to the drive of the account authenticated with
        #   `earthengine authenticate`
        id = feat['id']

        # Check if task already running for this feature
        if any(t['description'] == id and t['state'] in ['READY', 'RUNNING', 'COMPLETED'] for t in tasks):
            return

        image, params = self.get_image(feat, **kwargs)
        params['description'] = id
        params['folder'] = folder

        task = ee.batch.Export.image.toDrive(image, crs=crs, maxPixels=max_pixels, **params)
        ee.batch.data.exportImage(task.id, task.config)
