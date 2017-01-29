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

    def __init__(self, file_path):
        self.file_path = file_path

    def get_extent(self):
        # TODO
        self.extent = None

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





