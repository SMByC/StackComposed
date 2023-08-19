#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Stack Composed
#
#  Copyright (C) 2016-2023 Xavier C. Llano, SMBYC
#  Email: xavier.corredor.llano@gmail.com
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
import gc
import warnings
import numpy as np
from osgeo import gdal, osr
from dask.diagnostics import ProgressBar
warnings.filterwarnings('ignore')

from stack_composed import header
from stack_composed.image import Image
from stack_composed.stats import statistic

IMAGES_TYPES = ('.tif', '.TIF', '.img', '.IMG', '.hdr', '.HDR')


def run(stat, preproc, bands, nodata, output, output_type, num_process, chunksize, start_date, end_date, inputs):
    # ignore warnings
    print(header)

    # check statistical option
    if stat not in ('median', 'mean', 'gmean', 'max', 'min', 'std', 'valid_pixels', 'last_pixel',
                    'jday_last_pixel', 'jday_median', 'linear_trend') \
            and not stat.startswith(('extract_', 'percentile_', 'trim_mean_')):
        print("\nError: argument '-stat' invalid choice: {}".format(stat))
        print("choose from: extract_NN, median, mean, gmean, max, min, std, valid_pixels, last_pixel, "
              "jday_last_pixel, jday_median, linear_trend, percentile_NN, trim_mean_LL_UL")
        return
    if stat.startswith('extract_'):
        try:
            int(stat.split('_')[1])
        except:
            print("\nError: argument '-stat' invalid choice: {}".format(stat))
            print("the extract_NN must ends with a valid number, e.g. extract_2")
            return
    if stat.startswith('percentile_'):
        try:
            int(stat.split('_')[1])
        except:
            print("\nError: argument '-stat' invalid choice: {}".format(stat))
            print("the percentile must ends with a valid number, e.g. percentile_25")
            return
    if stat.startswith('trim_mean_'):
        try:
            int(stat.split('_')[2])
            int(stat.split('_')[3])
        except:
            print("\nError: argument '-stat' invalid choice: {}".format(stat))
            print("the trim_mean_LL_UL must ends with a valid limits, e.g. trim_mean_10_80")
            return

    # check preprocessing options
    if preproc is not None:
        if not preproc.startswith(('less_than_', 'greater_than_', 'between_', 'percentile_')) and \
            not preproc.endswith(('_std_devs', '_IQR')):
            print("\nError: argument '-preproc' invalid choice: {}".format(preproc))
            print("choose from: less_than_NN, greater_than_NN, between_LL_UL, percentile_LL_UL, NN_std_devs, NN_IQR")
            return
        if preproc.startswith('less_than_'):
            try:
                int(preproc.split('_')[2])
            except:
                print("\nError: argument '-preproc' invalid choice: {}".format(preproc))
                print("the less_than_NN must ends with a valid number, e.g. less_than_1000")
                return
        if preproc.startswith('greater_than_'):
            try:
                int(preproc.split('_')[2])
            except:
                print("\nError: argument '-preproc' invalid choice: {}".format(preproc))
                print("the greater_than_NN must ends with a valid number, e.g. greater_than_0")
                return
        if preproc.startswith('between_'):
            try:
                int(preproc.split('_')[1])
                int(preproc.split('_')[2])
            except:
                print("\nError: argument '-preproc' invalid choice: {}".format(preproc))
                print("the between_LL_UL must ends with a valid limits, e.g. between_0_1000")
                return
        if preproc.startswith('percentile_'):
            try:
                int(preproc.split('_')[1])
                int(preproc.split('_')[2])
            except:
                print("\nError: argument '-preproc' invalid choice: {}".format(preproc))
                print("the percentile_LL_UL must ends with a valid limits, e.g. percentile_10_90")
                return
        if preproc.endswith('_std_devs'):
            try:
                float(preproc.split('_')[0])
            except:
                print("\nError: argument '-preproc' invalid choice: {}".format(preproc))
                print("the NN_std_devs must starts with a valid number, e.g. 2.5_std_devs")
                return
        if preproc.endswith('_IQR'):
            try:
                float(preproc.split('_')[0])
            except:
                print("\nError: argument '-preproc' invalid choice: {}".format(preproc))
                print("the NN_IQR must starts with a valid number, e.g. 1.5_IQR")
                return

    print("\nLoading and prepare images in path(s):", flush=True)
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

    # filter images based on the start date and/or end date, required filename as metadata
    if start_date is not None or end_date is not None:
        [image.set_metadata_from_filename() for image in images]
        if start_date is not None:
            images = [image for image in images if image.date >= start_date]
        if end_date is not None:
            images = [image for image in images if image.date <= end_date]

    if len(images) <= 1:
        print("\n\nAfter load (and filter images in range date if applicable) there are {} images to process.\n"
              "StackComposed required at least 2 or more images to process.\n".format(len(images)))
        exit(1)

    # save nodata set from arguments
    for image in images: image.nodata_from_arg = nodata

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

    # reset the chunksize with the min of width/high if apply
    if chunksize > min(Image.wrapper_shape):
        chunksize = min(Image.wrapper_shape)

    # some information about process
    if len(images_files) != len(images):
        print("  images loaded: {0}".format(len(images_files)))
        print("  images to process: {0} (filtered in the range dates)".format(len(images)))
    else:
        print("  images to process: {0}".format(len(images)))
    print("  band(s) to process: {0}".format(','.join([str(b) for b in bands])))
    print("  pixels size: {0} x {1}".format(round(Image.wrapper_x_res, 1), round(Image.wrapper_y_res, 1)))
    print("  wrapper size: {0} x {1} pixels".format(Image.wrapper_shape[1], Image.wrapper_shape[0]))
    print("  running in {0} cores with chunks size {1}".format(num_process, chunksize))

    # check
    print("  checking bands and pixel size: ", flush=True, end="")
    for image in images:
        for band in bands:
            if band > image.n_bands:
                print("\n\nError: the image '{0}' don't have the band {1} needed to process\n"
                      .format(image.file_path, band))
                exit(1)
        if round(image.x_res, 1) != round(Image.wrapper_x_res, 1) or \
           round(image.y_res, 1) != round(Image.wrapper_y_res, 1):
            print("\n\nError: the image '{}' don't have the same pixel size to the base image: {}x{} vs {}x{}."
                  " The stack-composed is not enabled for process yet images with different pixel size.\n"
                  .format(image.file_path, round(image.x_res, 1), round(image.y_res, 1),
                          round(Image.wrapper_x_res, 1), round(Image.wrapper_x_res, 1)))
            exit(1)
    print("ok")

    # set bounds for all images
    [image.set_bounds() for image in images]

    # for some statistics that required filename as metadata
    if stat in ["last_pixel", "jday_last_pixel", "jday_median", "linear_trend"]:
        [image.set_metadata_from_filename() for image in images]

    # registered Dask progress bar
    pbar = ProgressBar()
    pbar.register()

    for band in bands:
        # check and set the output file before process
        if os.path.isdir(output):
            output_filename = os.path.join(output, "stack_composed_{}_band{}.tif".format(stat, band))
        elif output.endswith((".tif", ".TIF")) and os.path.isdir(os.path.dirname(output)):
            output_filename = output
        elif output.endswith((".tif", ".TIF")) and os.path.dirname(output) == '':
            output_filename = os.path.join(os.getcwd(), output)
        else:
            print("\nError: Setting the output filename, wrong directory and/or\n"
                  "       filename: {}\n".format(output))
            exit(1)

        if stat in ['linear_trend']:
            output_filename = output_filename.replace("stack_composed_linear_trend_band",
                                                      "stack_composed_linear_trend_x1e6_band")

        # choose the default data type based on the statistic
        if output_type is None:
            if stat in ['median', 'mean', 'gmean', 'max', 'min', 'last_pixel', 'jday_last_pixel',
                        'jday_median'] or stat.startswith(('extract_', 'percentile_', 'trim_mean_')):
                gdal_output_type = gdal.GDT_UInt16
            if stat in ['std', 'snr']:
                gdal_output_type = gdal.GDT_Float32
            if stat in ['valid_pixels']:
                if len(images) < 256:
                    gdal_output_type = gdal.GDT_Byte
                else:
                    gdal_output_type = gdal.GDT_UInt16
            if stat in ['linear_trend']:
                gdal_output_type = gdal.GDT_Int32
        else:
            if output_type == 'byte': gdal_output_type = gdal.GDT_Byte
            if output_type == 'uint16': gdal_output_type = gdal.GDT_UInt16
            if output_type == 'uint32': gdal_output_type = gdal.GDT_UInt32
            if output_type == 'int16': gdal_output_type = gdal.GDT_Int16
            if output_type == 'int32': gdal_output_type = gdal.GDT_Int32
            if output_type == 'float32': gdal_output_type = gdal.GDT_Float32
            if output_type == 'float64': gdal_output_type = gdal.GDT_Float64
        for image in images:
            image.output_type = gdal_output_type

        ### process ###
        # Calculate the statistics
        print("\nProcessing the {} for band {}:".format(stat, band))
        output_array = statistic(stat, preproc, images, band, num_process, chunksize)

        ### save result ###
        # create output raster
        driver = gdal.GetDriverByName('GTiff')
        nbands = 1
        outRaster = driver.Create(output_filename, Image.wrapper_shape[1], Image.wrapper_shape[0],
                                  nbands, gdal_output_type)
        outband = outRaster.GetRasterBand(nbands)

        # set the nodata to the output file
        if stat in ['linear_trend']:
            # convert nan value and set nodata value specific for linear trend
            output_array[np.isnan(output_array)] = -2147483648
            outband.SetNoDataValue(-2147483648)
        elif nodata is not None:
            outband.SetNoDataValue(nodata)
        else:
            # set the nodata based on the input files
            nodata_from_file = set([image.nodata_from_file[band] for image in images])
            if len(nodata_from_file) == 1:
                outband.SetNoDataValue(nodata_from_file.pop())
            elif None not in nodata_from_file:
                print("\nWarning: the nodata value is not set to the output file "
                      "because the input files have different nodata values.\n")

        # write band
        outband.WriteArray(output_array)

        # set projection and geotransform
        outRasterSRS = osr.SpatialReference()
        outRasterSRS.ImportFromWkt(Image.projection)
        outRaster.SetProjection(outRasterSRS.ExportToWkt())
        outRaster.SetGeoTransform((Image.wrapper_extent[0], Image.wrapper_x_res, 0,
                                   Image.wrapper_extent[1], 0, -Image.wrapper_y_res))

        # clean
        del driver, outRaster, outband, outRasterSRS, output_array
        # force run garbage collector to release unreferenced memory
        gc.collect()

    print("\nProcess completed!")



