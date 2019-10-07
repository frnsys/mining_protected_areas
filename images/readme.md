1. `python regions.py` to compute some high-level regions that contain all the protected areas and export TIFs of them.
    - Export to Google Drive tasks are run to export the images at a resolution of 1000m (higher resolutions result in massive file sizes).
    - Region metadata is saved to `data/regions.json`. Overall bounds of the protected areas are cached to `data/bounds.json`.
2. Download the region TIFs from Drive to `data/tif/`.
    - Some TIFs may be multipart. To merge, run: `gdalbuildvrt merged.vrt foo*.tif` and then `gdal_translate -of GTiff merged.vrt foo.tif`
3. `python clip.py` to clip out the individual protected area images from the exported region images.
    - Individual protected area images are exported to `data/img` as PNGs.
    - Metadata for each individual image (the box and bounds) are exported to `data/img/meta.json`.
    - The individually clipped protected images are then pasted into one global/world image saved to `data/img/world.png` and the metadata for that (the box) is saved to `data/img/world.json`. This is the image that is imported into the map as an overlay.
