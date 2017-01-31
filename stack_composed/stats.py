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
import numpy as np


def statistic(stat, images, band):
    # get the numpy 3rd dimension array stack of the bands in chunks (x_chunk and y_chunk)
    raster_layerstack = np.dstack([image.get_raster_band_adjusted(band) for image in images])

    # call built in numpy statistical functions, with a specified axis. if
    # axis=2 means it will calculate along the 'depth' axis, per pixel.
    # with the return being n by m, the shape of each band.
    #
    # Calculate the median statistical
    if stat == 'median':
        output_array = np.nanmedian(raster_layerstack, axis=2)
        return output_array
        # Calculate the mean statistical
