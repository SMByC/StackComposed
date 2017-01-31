#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Stack Composed
#
#  Copyright (C) 2016-2017 Xavier Corredor Llano, SMBYC
#  Email: xcorredorl at ideam.gov.co
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import os
import warnings
import gdal
import numpy as np

from stack_composed.image import Image
from stack_composed.stats import statistic

IMAGES_TYPES = ('.tif', '.TIF', 'img', 'IMG')

header = \
'''==============================================================

StackComposed

  Compute and generate the composed of a raster images stack

Run with '-h' for more options or visit the documentation:
https://smbyc.bitbucket.io/md/stackcomposed

Copyright (C) 2016-2017 Xavier Corredor Llano
Sistema de Monitoreo de Bosques y Carbono - SMBYC and FAO

=============================================================='''


def run(stat, bands, inputs, output, start_date=None, end_date=None):
    # ignore warnings
    warnings.filterwarnings("ignore")
    print(header)

    print("\nRead and loading images... ", end='')
    # search all Image files in inputs recursively if the files are in directories
    images_files = []
    for _input in inputs:
        if os.path.isfile(_input):
            if _input.endswith(IMAGES_TYPES):
                images_files.append(os.path.abspath(_input))
        elif os.path.isdir(_input):
            for root, dirs, files in os.walk(_input):
                if len(files) != 0:
                    files = [os.path.join(root, x) for x in files if x.endswith(IMAGES_TYPES)]
                    [images_files.append(os.path.abspath(file)) for file in files]

    # load bands
    if isinstance(bands, int):
        bands = [bands]
    if not isinstance(bands, list):
        bands = [int(b) for b in bands.split(',')]

    # load images
    images = [Image(landsat_file) for landsat_file in images_files]

    print("Done")
    print("  images to process: {0}".format(len(images_files)))
    print("  band(s) to process: {0}".format(','.join([str(b) for b in bands])))

    # get wrapper extent
    min_x = min([image.extent[0] for image in images])
    max_y = max([image.extent[1] for image in images])
    max_x = max([image.extent[2] for image in images])
    min_y = min([image.extent[3] for image in images])
    Image.wrapper_extent = [min_x, max_y, max_x, min_y]

    # define the properties for the raster wrapper
    Image.wrapper_x_res = images[0].x_res
    Image.wrapper_y_res = images[0].y_res
    Image.wrapper_shape = (int((max_y-min_y)/Image.wrapper_y_res), int((max_x-min_x)/Image.wrapper_x_res))  # (y,x)

    for band in bands:

        print("\nProcessing the {} for band {} in {} images... ".format(stat, band, len(images)), end='')

        # Calculate the statistics
        output_array = statistic(stat, images, band)

        #### save result
        output_filename = os.path.join(output, "stack_composed_{}_band{}.tif".format(stat, band))
        # create output raster
        driver = gdal.GetDriverByName('GTiff')
        nbands = 1
        outRaster = driver.Create(output_filename, Image.wrapper_shape[1], Image.wrapper_shape[0],
                                  nbands, gdal.GDT_Float32)

        # write bands
        outband = outRaster.GetRasterBand(nbands)
        outband.WriteArray(output_array)
        # nodata value
        outband.SetNoDataValue(np.nan)

        # set projection and geotransform
        outRaster.SetProjection(images[0].projection.ExportToWkt())
        outRaster.SetGeoTransform((Image.wrapper_extent[0], Image.wrapper_x_res, 0,
                                   Image.wrapper_extent[1], 0, -Image.wrapper_y_res))

        # clean
        outRaster = None

        print("Done")

    print("\nProcess completed!")



