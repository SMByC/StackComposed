#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2016-2025 Xavier C. Llano, SMBYC
#  Email: xavier.corredor.llano@gmail.com
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
import os
import numpy as np
from osgeo import gdal

from stack_composed.parse import parse_filename


class Image:
    # global wrapper matrix properties
    wrapper_extent = None
    wrapper_x_res = None
    wrapper_y_res = None
    wrapper_shape = None
    # global projection
    projection = None

    def __init__(self, file_path):
        self.file_path = self.get_dataset_path(file_path)
        ### set geoproperties ###
        self.gdal_file = gdal.Open(self.file_path, gdal.GA_ReadOnly)
        # setting the extent, pixel sizes and projection
        min_x, x_res, x_skew, max_y, y_skew, y_res = self.gdal_file.GetGeoTransform()
        max_x = min_x + (self.gdal_file.RasterXSize * x_res)
        min_y = max_y + (self.gdal_file.RasterYSize * y_res)
        # extent
        self.extent = [min_x, max_y, max_x, min_y]
        # pixel sizes
        self.x_res = abs(float(x_res))
        self.y_res = abs(float(y_res))
        # number of bands
        self.n_bands = self.gdal_file.RasterCount
        # no data values
        self.nodata_from_arg = None
        self.nodata_from_file = {band: self.gdal_file.GetRasterBand(band).GetNoDataValue() for band in range(1, self.n_bands + 1)}
        # projection
        if Image.projection is None:
            Image.projection = self.gdal_file.GetProjectionRef()
        # output type
        self.output_type = None
        self.gdal_file = None

    @staticmethod
    def get_dataset_path(file_path):
        path, ext = os.path.splitext(file_path)
        if ext.lower() == ".hdr":
            # search the dataset for ENVI files
            dataset_exts = ['.dat', '.raw', '.sli', '.hyspex', '.img']
            for test_ext in [''] + dataset_exts + [i.upper() for i in dataset_exts]:
                test_dataset_path = path + test_ext
                if os.path.isfile(test_dataset_path):
                    return test_dataset_path
        else:
            return file_path

    def set_bounds(self):
        # bounds for image with respect to wrapper
        # the 0,0 is left-upper corner
        self.xi_min = round((self.extent[0] - Image.wrapper_extent[0]) / Image.wrapper_x_res)
        self.xi_max = round(Image.wrapper_shape[1] - (Image.wrapper_extent[2] - self.extent[2]) / Image.wrapper_x_res)
        self.yi_min = round((Image.wrapper_extent[1] - self.extent[1]) / Image.wrapper_y_res)
        self.yi_max = round(Image.wrapper_shape[0] - (self.extent[3] - Image.wrapper_extent[3]) / Image.wrapper_y_res)

    def set_metadata_from_filename(self):
        self.landsat_version, self.sensor, self.path, self.row, self.date, self.jday = parse_filename(self.file_path)

    def get_chunk(self, band, xoff, xsize, yoff, ysize):
        """
        Get the array of the band for the respective chunk
        """
        if self.gdal_file is None:
            self.gdal_file = gdal.Open(self.file_path, gdal.GA_ReadOnly)
        raster_band = self.gdal_file.GetRasterBand(band).ReadAsArray(xoff, yoff, xsize, ysize).astype(np.float32)

        # convert the no data values from file to NaN
        if self.nodata_from_file[band] is not None:
            nodata_mask = raster_band == self.nodata_from_file[band]
            raster_band[nodata_mask] = np.nan

        # convert the no data values set from arguments to NaN
        if self.nodata_from_arg is not None and self.nodata_from_arg != self.nodata_from_file[band]:
            nodata_mask = raster_band == self.nodata_from_arg
            raster_band[nodata_mask] = np.nan

        return raster_band

    def get_chunk_in_wrapper(self, band, xc, xc_size, yc, yc_size):
        """
        Get the array of the band adjusted into the wrapper matrix for the respective chunk
        """
        # Calculate bounds for the chunk within the wrapper
        xc_min = xc
        xc_max = xc + xc_size
        yc_min = yc
        yc_max = yc + yc_size

        # Check if the chunk is outside the wrapper's bounds
        if xc_max <= self.xi_min or xc_min >= self.xi_max or yc_max <= self.yi_min or yc_min >= self.yi_max:
            return None

        # initialize the chunk with a nan matrix
        chunk_matrix = np.full((yc_size, xc_size), np.nan)

        # set bounds for get the array chunk in image
        xoff = 0 if xc_min <= self.xi_min else xc_min - self.xi_min
        xsize = xc_max - self.xi_min if xc_min <= self.xi_min else self.xi_max - xc_min
        yoff = 0 if yc_min <= self.yi_min else yc_min - self.yi_min
        ysize = yc_max - self.yi_min if yc_min <= self.yi_min else self.yi_max - yc_min

        # adjust to maximum size with respect to chunk or/and image
        xsize = xc_size if xsize > xc_size else xsize
        xsize = self.xi_max - self.xi_min if xsize > self.xi_max - self.xi_min else xsize
        ysize = yc_size if ysize > yc_size else ysize
        ysize = self.yi_max - self.yi_min if ysize > self.yi_max - self.yi_min else ysize

        # set bounds for fill in chunk matrix
        x_min = self.xi_min - xc_min if xc_min <= self.xi_min else 0
        x_max = x_min + xsize if x_min + xsize < xc_max else xc_max
        y_min = self.yi_min - yc_min if yc_min <= self.yi_min else 0
        y_max = y_min + ysize if y_min + ysize < yc_max else yc_max

        # fill with the chunk data of the image in the corresponding position
        chunk_matrix[y_min:y_max, x_min:x_max] = self.get_chunk(band, xoff, xsize, yoff, ysize)

        return chunk_matrix
