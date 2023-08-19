#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2016-2023 Xavier C. Llano, SMBYC
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
        self.nodata_from_file = [self.gdal_file.GetRasterBand(i).GetNoDataValue() for i in range(1, self.n_bands + 1)]
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

        # Calculate the overlapping region between chunk and wrapper
        x_start = max(xc_min, self.xi_min)
        x_end = min(xc_max, self.xi_max)
        y_start = max(yc_min, self.yi_min)
        y_end = min(yc_max, self.yi_max)

        # Calculate the offset and size for the get_chunk function
        xoff = max(0, x_start - self.xi_min)
        xsize = x_end - x_start
        yoff = max(0, y_start - self.yi_min)
        ysize = y_end - y_start

        # Get the chunk data from the main get_chunk function
        chunk_data = self.get_chunk(band, xoff, xsize, yoff, ysize)

        # Create a nan-filled chunk matrix
        chunk_matrix = np.full((yc_size, xc_size), np.nan)

        # Calculate the fill bounds within the chunk_matrix
        fill_x_start = max(0, xc_min - x_start)
        fill_x_end = min(xc_size, xc_max - x_start)
        fill_y_start = max(0, yc_min - y_start)
        fill_y_end = min(yc_size, yc_max - y_start)

        # Fill the overlapping region with the chunk data
        chunk_matrix[fill_y_start:fill_y_end, fill_x_start:fill_x_end] = \
            chunk_data[fill_y_start:fill_y_end, fill_x_start:fill_x_end]

        return chunk_matrix
