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
import operator
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

import dask.array as da
import numpy as np
import rasterio

from stack_composed.image import Image, reset_dataset_cache

# Safe operator dispatch — replaces eval() for -preproc CLI conditions.
_CMP_OPS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


def _build_stat_func(stat):
    """Return a vectorized ``(stack_chunk, metadata) -> 2D array`` function for ``stat``."""

    # Extract: keep only voxels equal to v, then per-pixel mean (NaN where empty).
    if stat.startswith("extract_"):
        v = int(stat.split("_")[1])

        def extract_stat(stack_chunk, metadata):
            masked = np.where(stack_chunk == v, stack_chunk, np.nan)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                return np.nanmean(masked, axis=2)
        return extract_stat

    if stat == "median":
        def median_stat(stack_chunk, metadata):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                return np.nanmedian(stack_chunk, axis=2)
        return median_stat

    if stat == "mean":
        def mean_stat(stack_chunk, metadata):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                return np.nanmean(stack_chunk, axis=2)
        return mean_stat

    # Geometric mean as exp(mean(log(x))) — naturally handles NaN, vectorized.
    # Non-positive values are dropped (log undefined); pixels with no valid
    # positive samples become NaN.
    if stat == "gmean":
        def gmean_stat(stack_chunk, metadata):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                positive = np.where(stack_chunk > 0, stack_chunk, np.nan)
                return np.exp(np.nanmean(np.log(positive), axis=2))
        return gmean_stat

    if stat == "sum":
        def sum_stat(stack_chunk, metadata):
            valid = np.count_nonzero(~np.isnan(stack_chunk), axis=2)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                total = np.nansum(stack_chunk, axis=2)
            return np.where(valid == 0, np.nan, total)
        return sum_stat

    if stat == "max":
        def max_stat(stack_chunk, metadata):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                return np.nanmax(stack_chunk, axis=2)
        return max_stat

    if stat == "min":
        def min_stat(stack_chunk, metadata):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                return np.nanmin(stack_chunk, axis=2)
        return min_stat

    if stat == "std":
        def std_stat(stack_chunk, metadata):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                return np.nanstd(stack_chunk, axis=2)
        return std_stat

    if stat == "valid_pixels":
        def valid_pixels_stat(stack_chunk, metadata):
            return np.count_nonzero(~np.isnan(stack_chunk), axis=2)
        return valid_pixels_stat

    if stat.startswith("percentile_"):
        p = int(stat.split("_")[1])

        def percentile_stat(stack_chunk, metadata):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                return np.nanpercentile(stack_chunk, p, axis=2)
        return percentile_stat

    if stat == "last_pixel":
        def last_pixel_stat(stack_chunk, metadata):
            # Sort layers most-recent-first, then take the first non-NaN per pixel.
            order = np.argsort(metadata["date"])[::-1]
            sorted_stack = stack_chunk[:, :, order]
            return _first_valid_along_axis(sorted_stack, sorted_stack)
        return last_pixel_stat

    if stat == "jday_last_pixel":
        def jday_last_pixel_stat(stack_chunk, metadata):
            order = np.argsort(metadata["date"])[::-1]
            sorted_stack = stack_chunk[:, :, order]
            jdays = np.asarray(metadata["jday"], dtype=np.float64)[order]
            jday_grid = np.broadcast_to(jdays, sorted_stack.shape)
            result = _first_valid_along_axis(sorted_stack, jday_grid)
            # Preserve historical behavior: all-NaN pixels emit 0 (uint16 output).
            return np.where(np.isnan(result), 0, result)
        return jday_last_pixel_stat

    if stat == "jday_median":
        def jday_median_stat(stack_chunk, metadata):
            order = np.argsort(metadata["date"])
            sorted_stack = stack_chunk[:, :, order]
            jdays = np.asarray(metadata["jday"], dtype=np.float64)[order]
            valid = ~np.isnan(sorted_stack)
            jday_grid = np.where(valid, np.broadcast_to(jdays, sorted_stack.shape), np.nan)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                med = np.nanmedian(jday_grid, axis=2)
            return np.where(np.isnan(med), 0, np.ceil(med))
        return jday_median_stat

    if stat.startswith("trim_mean_"):
        lower = int(stat.split("_")[2])
        upper = int(stat.split("_")[3])

        def trim_mean_stat(stack_chunk, metadata):
            return _trim_mean_axis2(stack_chunk, lower, upper)
        return trim_mean_stat

    if stat == "linear_trend":
        def linear_trend_stat(stack_chunk, metadata):
            order = np.argsort(metadata["date"])
            sorted_stack = stack_chunk[:, :, order]
            dates = np.asarray(metadata["date"])[order]
            # Days since the earliest date.
            epoch = dates[0]
            x_days = np.array(
                [(d - epoch).days for d in dates], dtype=np.float64
            )
            return _linear_trend_axis2(sorted_stack, x_days) * 1e6
        return linear_trend_stat

    raise ValueError(f"Unknown statistic: {stat!r}")


def _first_valid_along_axis(sorted_stack, values):
    """For each (y, x), return ``values`` at the first non-NaN layer of ``sorted_stack``.

    Both arrays share shape ``(H, W, N)`` and are sorted along the z-axis in the
    desired priority order.
    """
    valid = ~np.isnan(sorted_stack)
    # argmax returns 0 when all are False, so guard with an "any valid" mask.
    first_idx = valid.argmax(axis=2)
    H, W = sorted_stack.shape[:2]
    yy, xx = np.indices((H, W))
    picked = values[yy, xx, first_idx]
    any_valid = valid.any(axis=2)
    return np.where(any_valid, picked, np.nan)


def _trim_mean_axis2(stack_chunk, lower, upper):
    """Vectorized trimmed-mean along axis=2 with percentile bounds.

    For pixels with <= 2 valid samples, falls back to the percentile at the midpoint
    (matching the original per-pixel behavior).
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        lo = np.nanpercentile(stack_chunk, lower, axis=2)
        hi = np.nanpercentile(stack_chunk, upper, axis=2)
        valid = ~np.isnan(stack_chunk)
        n_valid = valid.sum(axis=2)

        in_range = (stack_chunk >= lo[..., None]) & (stack_chunk <= hi[..., None]) & valid
        # avoid division by zero — mark as NaN later
        clean = np.where(in_range, stack_chunk, np.nan)
        trimmed = np.nanmean(clean, axis=2)

        fallback = np.nanpercentile(stack_chunk, (lower + upper) / 2.0, axis=2)
        result = np.where(n_valid <= 2, fallback, trimmed)
        # all-NaN pixels emit 0 to preserve the historical multiprocessing-safe value
        return np.where(n_valid == 0, 0, result)


def _linear_trend_axis2(sorted_stack, x_days):
    """Vectorized linear regression slope along axis=2.

    Returns NaN when fewer than 2 valid samples exist for a pixel.
    """
    valid = ~np.isnan(sorted_stack)
    n_valid = valid.sum(axis=2)

    y = np.where(valid, sorted_stack, 0.0)
    x = np.broadcast_to(x_days, sorted_stack.shape)
    x_masked = np.where(valid, x, 0.0)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        n = n_valid.astype(np.float64)
        sum_x = x_masked.sum(axis=2)
        sum_y = y.sum(axis=2)
        sum_xy = (x_masked * y).sum(axis=2)
        sum_xx = (x_masked * x_masked).sum(axis=2)

        # mean over valid samples only
        mean_x = np.where(n > 0, sum_x / n, np.nan)
        mean_y = np.where(n > 0, sum_y / n, np.nan)

        ssxym = sum_xy / np.where(n > 0, n, 1) - mean_x * mean_y
        ssxm = sum_xx / np.where(n > 0, n, 1) - mean_x * mean_x

        slope = np.where(ssxm > 0, ssxym / ssxm, np.nan)
        slope = np.where(n_valid < 2, np.nan, slope)
    return slope


# --- worker pool plumbing -------------------------------------------------

# Per-worker process state, set up by ``_init_worker``.
_WORKER = {}


def _init_worker(images, band, stat, preproc_arg, wrapper_state):
    """ProcessPoolExecutor initializer: prebuild stat/preproc functions and share state."""
    # New process inherits no open dataset handles; ensure the cache starts clean.
    reset_dataset_cache()
    # Restore class-level wrapper geometry that workers need for chunk indexing.
    Image.wrapper_extent = wrapper_state["wrapper_extent"]
    Image.wrapper_x_res = wrapper_state["wrapper_x_res"]
    Image.wrapper_y_res = wrapper_state["wrapper_y_res"]
    Image.wrapper_shape = wrapper_state["wrapper_shape"]
    Image.projection = wrapper_state["projection"]
    for img in images:
        img.set_bounds()
    _WORKER["images"] = images
    _WORKER["band"] = band
    _WORKER["stat"] = stat
    _WORKER["stat_func"] = _build_stat_func(stat)
    _WORKER["preproc_func"] = _build_preproc_func(preproc_arg)


def _compute_chunk(task):
    """Compute one chunk in a worker; returns ``(window_tuple, array)``.

    Always returns an array of shape ``(yc_size, xc_size)`` so the writer can
    overwrite the empty output uniformly; fully-empty chunks become NaN.
    """
    block_id, block_shape, chunksize = task
    yc = block_id[0] * chunksize
    xc = block_id[1] * chunksize
    yc_size, xc_size = block_shape

    images = _WORKER["images"]
    band = _WORKER["band"]
    stat = _WORKER["stat"]
    stat_func = _WORKER["stat_func"]
    preproc_func = _WORKER["preproc_func"]

    raw_chunks = [img.get_chunk_in_wrapper(band, xc, xc_size, yc, yc_size) for img in images]
    mask_none = [c is not None for c in raw_chunks]
    valid_chunks = [c for c in raw_chunks if c is not None]

    if not valid_chunks:
        return (xc, yc, xc_size, yc_size), np.full((yc_size, xc_size), np.nan)

    stack = np.empty((yc_size, xc_size, len(valid_chunks)), dtype=np.float32)
    for k, c in enumerate(valid_chunks):
        stack[:, :, k] = c
    data_chunk = preproc_func(stack)

    if np.all(np.isnan(data_chunk)):
        return (xc, yc, xc_size, yc_size), np.full((yc_size, xc_size), np.nan)

    metadata = {}
    if stat in {"last_pixel", "jday_last_pixel", "jday_median", "linear_trend"}:
        metadata["date"] = np.array([img.date for img in images])[mask_none]
    if stat in {"jday_last_pixel", "jday_median"}:
        metadata["jday"] = np.array([img.jday for img in images])[mask_none]
    result = stat_func(data_chunk, metadata)
    return (xc, yc, xc_size, yc_size), result


def _window_from_tuple(window):
    xc, yc, xc_size, yc_size = window
    return ((yc, yc + yc_size), (xc, xc + xc_size))


def _build_preproc_func(preproc_arg):
    """Module-level (picklable) builder for the preprocess function."""
    return ChunkProcessor(preproc_arg)._setup_preprocess()


def _emit_progress(done, total):
    if total <= 0:
        return
    bar_width = 40
    filled = int(bar_width * done / total)
    bar = "#" * filled + " " * (bar_width - filled)
    pct = int(100 * done / total)
    end = "\n" if done == total else ""
    sys.stdout.write(f"\r[{bar}] {pct}% Completed ({done}/{total} chunks){end}")
    sys.stdout.flush()


def statistic(stat, preproc, images, band, num_process, chunksize, output_file):
    """Compute the stack composed for a single band and write it chunk-by-chunk.

    Workers compute chunks in parallel and stream results back; the main process
    is the sole writer, so no cross-process file lock is needed.
    """
    # Use dask's chunk planner only to derive a tidy chunk layout from the shape.
    wrapper_array = da.empty(Image.wrapper_shape, chunks=chunksize)
    chunksize = wrapper_array.chunks[0][0]
    delayed_blocks = wrapper_array.to_delayed()

    tasks = []
    for i in range(delayed_blocks.shape[0]):
        for j in range(delayed_blocks.shape[1]):
            # The actual block shape may shrink near the right/bottom edge.
            row_size = wrapper_array.chunks[0][i]
            col_size = wrapper_array.chunks[1][j]
            tasks.append(((i, j), (row_size, col_size), chunksize))

    total = len(tasks)
    if total == 0:
        return

    wrapper_state = {
        "wrapper_extent": Image.wrapper_extent,
        "wrapper_x_res": Image.wrapper_x_res,
        "wrapper_y_res": Image.wrapper_y_res,
        "wrapper_shape": Image.wrapper_shape,
        "projection": Image.projection,
    }

    _emit_progress(0, total)
    try:
        with rasterio.open(output_file, "r+") as dst:
            if num_process <= 1:
                # Single-process path: avoids fork overhead and is easier to debug.
                _init_worker(images, band, stat, preproc, wrapper_state)
                done = 0
                for task in tasks:
                    window, data = _compute_chunk(task)
                    dst.write(data, 1, window=_window_from_tuple(window))
                    done += 1
                    _emit_progress(done, total)
            else:
                with ProcessPoolExecutor(
                    max_workers=num_process,
                    initializer=_init_worker,
                    initargs=(images, band, stat, preproc, wrapper_state),
                ) as executor:
                    futures = [executor.submit(_compute_chunk, t) for t in tasks]
                    done = 0
                    for fut in as_completed(futures):
                        window, data = fut.result()
                        dst.write(data, 1, window=_window_from_tuple(window))
                        done += 1
                        _emit_progress(done, total)
    finally:
        reset_dataset_cache()
        _WORKER.clear()


class ChunkProcessor:
    """Build a per-chunk preprocessing function.

    Kept as a thin builder so ``_setup_preprocess`` can construct any of the
    supported preproc closures without needing the full processing context.
    """

    def __init__(self, preproc_arg):
        self.preproc_arg = preproc_arg

    def _setup_preprocess(self):
        arg = self.preproc_arg

        if arg is None:
            return lambda chunks: chunks

        if isinstance(arg, (int, float)):
            threshold = float(arg)

            def preproc_function(chunks):
                return np.where(chunks > threshold, chunks, np.nan)

            return preproc_function

        if isinstance(arg, list):
            # Each item is [operator_str, threshold].
            ops = [(_CMP_OPS[op], float(thr)) for op, thr in arg]

            def preproc_function(chunks):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    mask = np.ones(chunks.shape, dtype=bool)
                    for op, thr in ops:
                        mask &= op(chunks, thr)
                return np.where(mask, chunks, np.nan)

            return preproc_function

        if arg.startswith("percentile_"):
            lower = int(arg.split("_")[1])
            upper = int(arg.split("_")[2])

            def preproc_function(chunks):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    lo = np.nanpercentile(chunks, lower, axis=2, keepdims=True)
                    hi = np.nanpercentile(chunks, upper, axis=2, keepdims=True)
                    mask = (chunks >= lo) & (chunks <= hi)
                return np.where(mask, chunks, np.nan)

            return preproc_function

        if arg.endswith("_std_devs"):
            N = float(arg.split("_")[0])

            def preproc_function(chunks):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    mean = np.nanmean(chunks, axis=2, keepdims=True)
                    std = np.nanstd(chunks, axis=2, keepdims=True)
                    mask = (chunks >= mean - N * std) & (chunks <= mean + N * std)
                return np.where(mask, chunks, np.nan)

            return preproc_function

        if arg.endswith("_IQR"):
            N = float(arg.split("_")[0])

            def preproc_function(chunks):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    q25 = np.nanpercentile(chunks, 25, axis=2, keepdims=True)
                    q75 = np.nanpercentile(chunks, 75, axis=2, keepdims=True)
                    iqr = q75 - q25
                    mask = (chunks >= q25 - N * iqr) & (chunks <= q75 + N * iqr)
                return np.where(mask, chunks, np.nan)

            return preproc_function

        raise ValueError(f"Unknown preproc argument: {arg!r}")
