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
import dask.array as da
import numpy as np

from stack_composed.image import Image


def statistic(stat, preproc, images, band, num_process, chunksize):
    # create an empty initial wrapper raster for managed dask parallel
    # in chunks and storage result
    wrapper_array = da.empty(Image.wrapper_shape, chunks=chunksize)
    chunksize = wrapper_array.chunks[0][0]

    # call built in numpy statistical functions, with a specified axis. if
    # axis=2 means it will Compute along the 'depth' axis, per pixel.
    # with the return being n by m, the shape of each band.
    #

    # Extract the value NN
    if stat.startswith('extract_'):
        v = int(stat.split('_')[1])

        # Extract the value NN any other values will be nan
        def stat_func(stack_chunk, metadata):
            stack_chunk[stack_chunk != v] = np.nan
            return np.nanmean(stack_chunk, axis=2)

    # Compute the median
    if stat == 'median':
        def stat_func(stack_chunk, metadata):
            return np.nanmedian(stack_chunk, axis=2)

    # Compute the arithmetic mean
    if stat == 'mean':
        def stat_func(stack_chunk, metadata):
            return np.nanmean(stack_chunk, axis=2)

    # Compute the geometric mean
    if stat == 'gmean':
        def stat_func(stack_chunk, metadata):
            product = np.nanprod(stack_chunk, axis=2)
            count = np.count_nonzero(np.nan_to_num(stack_chunk), axis=2)
            gmean = np.array([p ** (1.0 / c) for p, c in zip(product, count)])
            gmean[gmean == 1] = np.nan
            return gmean

    # Compute the sum of the pixels values
    if stat == 'sum':
        def stat_func(stack_chunk, metadata):
            return np.nansum(stack_chunk, axis=2)

    # Compute the maximum value
    if stat == 'max':
        def stat_func(stack_chunk, metadata):
            return np.nanmax(stack_chunk, axis=2)

    # Compute the minimum value
    if stat == 'min':
        def stat_func(stack_chunk, metadata):
            return np.nanmin(stack_chunk, axis=2)

    # Compute the standard deviation
    if stat == 'std':
        def stat_func(stack_chunk, metadata):
            return np.nanstd(stack_chunk, axis=2)

    # Compute the valid pixels
    # this count the valid data (no nans) across the z-axis
    if stat == 'valid_pixels':
        def stat_func(stack_chunk, metadata):
            return stack_chunk.shape[2] - np.isnan(stack_chunk).sum(axis=2)

    # Compute the percentile NN
    if stat.startswith('percentile_'):
        p = int(stat.split('_')[1])
        def stat_func(stack_chunk, metadata):
            return np.nanpercentile(stack_chunk, p, axis=2)

    # Compute the last valid pixel
    if stat == 'last_pixel':
        def last_pixel(pixel_time_series, index_sort):
            if np.isnan(pixel_time_series).all():
                return np.nan
            for index in index_sort:
                if not np.isnan(pixel_time_series[index]):
                    return pixel_time_series[index]

        def stat_func(stack_chunk, metadata):
            index_sort = np.argsort(metadata['date'])[::-1]  # from the most recent to the oldest
            return np.apply_along_axis(last_pixel, 2, stack_chunk, index_sort)

    # Compute the julian day of the last valid pixel
    if stat == 'jday_last_pixel':
        def jday_last_pixel(pixel_time_series, index_sort, jdays):
            if np.isnan(pixel_time_series).all():
                return 0  # better np.nan but there is bug with multiprocessing with return nan value here
            for index in index_sort:
                if not np.isnan(pixel_time_series[index]):
                    return jdays[index]

        def stat_func(stack_chunk, metadata):
            index_sort = np.argsort(metadata['date'])[::-1]  # from the most recent to the oldest
            return np.apply_along_axis(jday_last_pixel, 2, stack_chunk, index_sort, metadata['jday'])

    # Compute the julian day of the median value
    if stat == 'jday_median':
        def jday_median(pixel_time_series, index_sort, jdays):
            if np.isnan(pixel_time_series).all():
                return 0  # better np.nan but there is bug with multiprocessing with return nan value here
            jdays = [jdays[index] for index in index_sort if not np.isnan(pixel_time_series[index])]
            return np.ceil(np.median(jdays))

        def stat_func(stack_chunk, metadata):
            index_sort = np.argsort(metadata['date'])  # from the oldest to most recent
            return np.apply_along_axis(jday_median, 2, stack_chunk, index_sort, metadata['jday'])

    # Compute the trimmed median with lower limit and upper limit
    if stat.startswith('trim_mean_'):
        # TODO: check this stats when the time series have few data
        lower = int(stat.split('_')[2])
        upper = int(stat.split('_')[3])
        def trim_mean(pixel_time_series):
            if np.isnan(pixel_time_series).all():
                return 0  # better np.nan but there is bug with multiprocessing with return nan value here
            pts = pixel_time_series[~np.isnan(pixel_time_series)]
            if len(pts) <= 2:
                return np.percentile(pts, (lower+upper)/2)
            return np.mean(pts[(pts >= np.percentile(pts, lower)) & (pts <= np.percentile(pts, upper))])

        def stat_func(stack_chunk, metadata):
            return np.apply_along_axis(trim_mean, 2, stack_chunk)

    # Compute the linear trend using least-squares method
    if stat == 'linear_trend':
        def linear_trend(pixel_time_series, index_sort, date_list):
            if np.isnan(pixel_time_series).all() or len(pixel_time_series[~np.isnan(pixel_time_series)]) == 1:
                return np.nan
            # Convert dates to Unix timestamp in days, then get the diff from minimum
            x = [int(int(date_list[index].strftime("%s")) / 86400) for index in index_sort]
            min_x = x[0]
            x = [i - min_x for i in x]  # diff from minimum

            # Get pixel data as a properly masked numpy array
            pts = [pixel_time_series[index] for index in index_sort]
            y = np.ma.array(pts, mask=np.isnan(pts))

            ssxm, ssxym, ssyxm, ssym = np.ma.cov(x, y, bias=1).flat
            slope = ssxym / ssxm

            return slope * 1e6

        def stat_func(stack_chunk, metadata):
            index_sort = np.argsort(metadata['date'])  # from the oldest to most recent
            return np.apply_along_axis(linear_trend, 2, stack_chunk, index_sort, metadata['date'])

    # Create an instance of BlockCalculator
    block_calculator = BlockCalculator(images, band, stat, stat_func, preproc)

    # Process
    map_blocks = da.map_blocks(block_calculator.calculate, wrapper_array,
                               chunks=wrapper_array.chunks, chunksize=chunksize, dtype=float)
    result_array = map_blocks.compute(num_workers=num_process, scheduler="processes")

    return result_array


class BlockCalculator:
    """Compute the statistical for the respective chunk"""
    def __init__(self, images, band, stat, stat_func, preproc_arg):
        self.images = images
        self.band = band
        self.stat_func = stat_func
        self.stat = stat
        self.preproc_arg = preproc_arg
        self.preproc_func = self._setup_preprocess()

    def _setup_preprocess(self):

        if self.preproc_arg is None:
            def preproc_function(chunks):
                return chunks
            return preproc_function

        if isinstance(self.preproc_arg, list):
            def preproc_function(chunks):
                for condition in self.preproc_arg:
                    operator, threshold = condition[0], condition[1]
                    eval_string = f'chunks {operator} {threshold}'
                    mask = eval(eval_string)
                    chunks = np.where(mask, chunks, np.nan)
                return chunks
            return preproc_function

        if self.preproc_arg.startswith('percentile_'):
            def percentile(pixel_ts, lower, upper):
                mask = np.logical_and(pixel_ts >= np.nanpercentile(pixel_ts, lower),
                                      pixel_ts <= np.nanpercentile(pixel_ts, upper))
                return np.where(mask, pixel_ts, np.nan)
            def preproc_function(chunks):
                lower = int(self.preproc_arg.split('_')[1])
                upper = int(self.preproc_arg.split('_')[2])
                return np.apply_along_axis(percentile, 2, chunks, lower, upper)
            return preproc_function

        if self.preproc_arg.endswith('_std_devs'):
            def std_devs(pixel_ts, N):
                mask = np.logical_and(pixel_ts >= np.nanmean(pixel_ts) - N * np.nanstd(pixel_ts),
                                      pixel_ts <= np.nanmean(pixel_ts) + N * np.nanstd(pixel_ts))
                return np.where(mask, pixel_ts, np.nan)
            def preproc_function(chunks):
                N = float(self.preproc_arg.split('_')[0])
                return np.apply_along_axis(std_devs, 2, chunks, N)
            return preproc_function

        if self.preproc_arg.endswith('_IQR'):
            def IQR(pixel_ts, N):
                # outliers using N interquartile range (IQR)
                mask = np.logical_and(pixel_ts >= np.nanpercentile(pixel_ts, 25) - N * (np.nanpercentile(pixel_ts, 75) - np.nanpercentile(pixel_ts, 25)),
                                      pixel_ts <= np.nanpercentile(pixel_ts, 75) + N * (np.nanpercentile(pixel_ts, 75) - np.nanpercentile(pixel_ts, 25)))
                return np.where(mask, pixel_ts, np.nan)
            def preproc_function(chunks):
                N = float(self.preproc_arg.split('_')[0])
                return np.apply_along_axis(IQR, 2, chunks, N)
            return preproc_function

    def _preprocess(self, chunks):
        return self.preproc_func(chunks)

    def _prepare_data(self, xc, yc, xc_size, yc_size):
        # get chunks
        chunks = np.array([image.get_chunk_in_wrapper(self.band, xc, xc_size, yc, yc_size) for image in self.images], dtype=object)

        # clean empty chunks and stack it
        self.mask_none = [False if chunk is None else True for chunk in chunks]
        chunks_masked = chunks[self.mask_none]
        if chunks_masked.size != 0:
            chunks_stack = np.stack(chunks[self.mask_none], axis=2).astype(float)
        else:
            return np.array(np.nan)

        # preprocess
        chunks_data = self._preprocess(chunks_stack)

        return chunks_data

    def _prepare_metadata(self):
        metadata = {}
        if self.stat in ["last_pixel", "jday_last_pixel", "jday_median", "linear_trend"]:
            metadata["date"] = np.array([image.date for image in self.images])[self.mask_none]
        if self.stat in ["jday_last_pixel", "jday_median"]:
            metadata["jday"] = np.array([image.jday for image in self.images])[self.mask_none]
        return metadata

    def calculate(self, block, block_id, chunksize):
        yc = block_id[0] * chunksize
        xc = block_id[1] * chunksize
        yc_size, xc_size = block.shape

        chunks_data = self._prepare_data(xc, yc, xc_size, yc_size)

        if chunks_data is None or np.all(np.isnan(chunks_data)):
            return np.full((yc_size, xc_size), np.nan)

        metadata = self._prepare_metadata()

        return self.stat_func(chunks_data, metadata)


