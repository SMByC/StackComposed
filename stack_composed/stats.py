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
from dask import multiprocessing

from stack_composed.image import Image


def statistic(stat, images, band, num_process, chunksize):
    # create a empty initial wrapper raster for managed dask parallel
    # in chunks and storage result
    wrapper_array = da.empty(Image.wrapper_shape, chunks=chunksize)
    chunksize = wrapper_array.chunks[0][0]

    # call built in numpy statistical functions, with a specified axis. if
    # axis=2 means it will calculate along the 'depth' axis, per pixel.
    # with the return being n by m, the shape of each band.
    #
    # Calculate the median statistical
    if stat == 'median':
        def stat_func(stack_chunk):
            return np.nanmedian(stack_chunk, axis=2)
    # Calculate the mean statistical
    if stat == 'mean':
        def stat_func(stack_chunk):
            return np.nanmean(stack_chunk, axis=2)
    # Calculate the maximum statistical
    if stat == 'max':
        def stat_func(stack_chunk):
            return np.nanmax(stack_chunk, axis=2)
    # Calculate the minimum statistical
    if stat == 'min':
        def stat_func(stack_chunk):
            return np.nanmin(stack_chunk, axis=2)
    # Calculate the standard deviation statistical
    if stat == 'std':
        def stat_func(stack_chunk):
            return np.nanstd(stack_chunk, axis=2)
    # Calculate the valid pixels statistical
    # this count the valid data (no nans) across the z-axis
    if stat == 'valid_pixels':
        def stat_func(stack_chunk):
            return stack_chunk.shape[2] - np.isnan(stack_chunk).sum(axis=2)
    # Calculate the percentile NN
    if stat.startswith('percentile_'):
        p = int(stat.split('_')[1])
        def stat_func(stack_chunk):
            return np.nanpercentile(stack_chunk, p, axis=2)

    # calculate the statistical for the respective chunk
    def calc(block, block_id=None, chunksize=None):
        yc = block_id[0] * chunksize
        yc_size = block.shape[0]
        xc = block_id[1] * chunksize
        xc_size = block.shape[1]

        # make stack reading all images only in specific chunk
        chunks_list = [image.get_chunk_in_wrapper(band, xc, xc_size, yc, yc_size) for image in images]
        chunks_list = np.array([i for i in chunks_list if i is not None])

        if not chunks_list.size:
            # all chunks are empty, return the chunk with nan
            return np.full((yc_size, xc_size), np.nan)

        stack_chunk = np.stack(chunks_list, axis=2)
        return stat_func(stack_chunk)

    # process
    map_blocks = da.map_blocks(calc, wrapper_array, chunks=wrapper_array.chunks, chunksize=chunksize, dtype=float)
    result_array = map_blocks.compute(num_workers=num_process, get=multiprocessing.get)

    return result_array
