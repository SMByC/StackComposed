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
import numpy as np

from stack_composed.image import Image


def statistic(stat, images, band):
    # create a empty initial wrapper raster for managed dask parallel
    # in chunks and storage result
    chunksize = 500
    wrapper_array = da.empty(Image.wrapper_shape, chunks=chunksize)

    # create a 3d raster stack with dask
    list_stack = [da.from_array(image.get_wrapper_raster_band(band), (1000, 1000)) for image in images]
    da_raster_stack = da.dstack(list_stack)
    da_raster_stack = da_raster_stack.rechunk(1000, 1000, len(list_stack))

    # call built in numpy statistical functions, with a specified axis. if
    # axis=2 means it will calculate along the 'depth' axis, per pixel.
    # with the return being n by m, the shape of each band.
    #
    # Calculate the median statistical
    if stat == 'median':
        def stat_func(stack_chunk):
            return np.nanmean(stack_chunk, axis=2)
    # Calculate the mean statistical

    def calc(block, block_id=None, chunksize=None):
        y = block_id[0] * chunksize
        y_size = block.shape[0]
        x = block_id[1] * chunksize
        x_size = block.shape[1]

        # make stack reading all images only in specific chunk
        stack_chunk = np.stack([image.get_wrapper_raster_band(band)[y:y + y_size, x:x + x_size]
                                for image in images], axis=2)

        return stat_func(stack_chunk)

    map_blocks = da.map_blocks(calc, wrapper_array, chunks=wrapper_array.chunks, chunksize=chunksize)
    result_array = map_blocks.compute(num_workers=1)

    return result_array
