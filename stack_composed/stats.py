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
import dask.array as da


def statistic(stat, images, band):
    # create a 3d raster stack with dask
    list_stack = [da.from_array(image.get_raster_band_adjusted(band), (1000, 1000)) for image in images]
    da_raster_stack = da.dstack(list_stack)
    # stack = stack.rechunk(5,5,1)

    # call built in numpy statistical functions, with a specified axis. if
    # axis=2 means it will calculate along the 'depth' axis, per pixel.
    # with the return being n by m, the shape of each band.
    #
    # Calculate the median statistical
    if stat == 'median':
        output_array = da.nanmean(da_raster_stack, axis=2).compute()
        return output_array
        # Calculate the mean statistical
