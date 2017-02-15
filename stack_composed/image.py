#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2016-2017 Xavier Corredor Llano, SMBYC
#  Email: xcorredorl at ideam.gov.co
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
import gdal
import numpy as np

from stack_composed.parse import parse_filename


class Image:
    wrapper_extent = None
    wrapper_x_res = None
    wrapper_y_res = None
    wrapper_shape = None

    def __init__(self, file_path):
        self.file_path = file_path
        # setting the extent, pixel sizes and projection
        self.get_geoproperties()

    def get_geoproperties(self):
        data = gdal.Open(self.file_path, gdal.GA_ReadOnly)
        min_x, x_res, x_skew, max_y, y_skew, y_res = data.GetGeoTransform()
        max_x = min_x + (data.RasterXSize * x_res)
        min_y = max_y + (data.RasterYSize * y_res)
        # extent
        #self.extent = [round(min_x, 5), round(max_y, 5), round(max_x, 5), round(min_y, 5)]
        self.extent = [min_x, max_y, max_x, min_y]
        # pixel sizes
        self.x_res = abs(float(x_res))
        self.y_res = abs(float(y_res))
        # projection
        outRasterSRS = gdal.osr.SpatialReference()
        outRasterSRS.ImportFromWkt(data.GetProjectionRef())
        self.projection = outRasterSRS
        data = None

    def get_metadata(self):
        # TODO
        print(parse_filename(self.file_path))

    def get_raster_band(self, band):
        dataset = gdal.Open(self.file_path, gdal.GA_ReadOnly)
        raster_band = dataset.GetRasterBand(band).ReadAsArray()
        raster_band = raster_band.astype(np.float32)

        # convert the no data value and zero to NaN
        no_data_value = dataset.GetRasterBand(band).GetNoDataValue()
        raster_band[raster_band == no_data_value] = np.nan

        return raster_band

    def get_wrapper_raster_band(self, band):
        """
        Get the raster band adjusted into the wrapper matrix
        """
        # get from:to x and y for put this raster data into the wrapper matrix
        # the count (from:to) starts from left-upper corner
        xw_min = round((self.extent[0] - Image.wrapper_extent[0]) / Image.wrapper_x_res)
        xw_max = round(Image.wrapper_shape[1] - (Image.wrapper_extent[2] - self.extent[2]) / Image.wrapper_x_res)
        yw_min = round((Image.wrapper_extent[1] - self.extent[1]) / Image.wrapper_y_res)
        yw_max = round(Image.wrapper_shape[0] - (self.extent[3] - Image.wrapper_extent[3]) / Image.wrapper_y_res)
        # create a nan matrix wrapper
        wrapper_matrix = np.full(Image.wrapper_shape, np.nan)
        # fill with the raster data in the corresponding position
        wrapper_matrix[yw_min:yw_max, xw_min:xw_max] = self.get_raster_band(band)

        return wrapper_matrix



