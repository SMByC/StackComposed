#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2016-2026 Xavier C. Llano, SMBYC
#  Email: xavier.corredor.llano@gmail.com
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
import os
from typing import ClassVar

import numpy as np
import rasterio
from rasterio.crs import CRS

from core.parse import parse_filename

# ENVI dataset extensions to probe when an ".hdr" path is given.
_ENVI_DATASET_EXTS = ("", ".dat", ".raw", ".sli", ".hyspex", ".img")

# Per-process cache of opened rasterio datasets. Workers reuse handles across
# chunks within their lifetime; the OS reclaims them at process exit.
_DATASET_CACHE: dict = {}


def _open_dataset(file_path):
    ds = _DATASET_CACHE.get(file_path)
    if ds is None:
        ds = rasterio.open(file_path)
        _DATASET_CACHE[file_path] = ds
    return ds


def reset_dataset_cache():
    """Drop any cached rasterio handles. Safe to call in worker initializers."""
    for ds in _DATASET_CACHE.values():
        try:
            ds.close()
        except Exception:
            pass
    _DATASET_CACHE.clear()


class Image:
    # global wrapper matrix properties
    wrapper_extent: ClassVar[list[float] | None] = None
    wrapper_x_res: ClassVar[float | None] = None
    wrapper_y_res: ClassVar[float | None] = None
    wrapper_shape: ClassVar[tuple[int, int] | None] = None
    # global projection
    projection: ClassVar[CRS | None] = None

    def __init__(self, file_path):
        self.file_path = self.get_dataset_path(file_path)
        with rasterio.open(self.file_path) as src:
            min_x = src.transform[2]
            x_res = src.transform[0]
            max_y = src.transform[5]
            y_res = src.transform[4]
            max_x = min_x + (src.width * x_res)
            min_y = max_y + (src.height * y_res)
            self.extent = [min_x, max_y, max_x, min_y]
            self.x_res = abs(float(x_res))
            self.y_res = abs(float(y_res))
            self.n_bands = src.count
            self.nodata_from_arg = None
            self.nodata_from_file = {b: src.nodatavals[b - 1] for b in range(1, self.n_bands + 1)}
            if Image.projection is None:
                Image.projection = src.crs
            self.data_type = {b: src.dtypes[b - 1] for b in range(1, self.n_bands + 1)}

    @staticmethod
    def get_dataset_path(file_path):
        path, ext = os.path.splitext(file_path)
        if ext.lower() != ".hdr":
            return file_path
        # ENVI: probe for a matching dataset alongside the .hdr.
        candidates = list(_ENVI_DATASET_EXTS) + [e.upper() for e in _ENVI_DATASET_EXTS if e]
        for test_ext in candidates:
            test_dataset_path = path + test_ext
            if os.path.isfile(test_dataset_path):
                return test_dataset_path
        raise FileNotFoundError(
            f"Could not locate ENVI dataset for header file: {file_path}"
        )

    def set_bounds(self):
        wrapper_extent = Image.wrapper_extent
        wrapper_x_res = Image.wrapper_x_res
        wrapper_y_res = Image.wrapper_y_res
        wrapper_shape = Image.wrapper_shape
        if (wrapper_extent is None or wrapper_x_res is None
                or wrapper_y_res is None or wrapper_shape is None):
            raise RuntimeError("Image wrapper state is not initialized")
        # bounds for image with respect to wrapper, 0,0 is left-upper corner
        self.xi_min = round((self.extent[0] - wrapper_extent[0]) / wrapper_x_res)
        self.xi_max = round(wrapper_shape[1] - (wrapper_extent[2] - self.extent[2]) / wrapper_x_res)
        self.yi_min = round((wrapper_extent[1] - self.extent[1]) / wrapper_y_res)
        self.yi_max = round(wrapper_shape[0] - (self.extent[3] - wrapper_extent[3]) / wrapper_y_res)

    def set_metadata_from_filename(self):
        self.landsat_version, self.sensor, self.path, self.row, self.date, self.jday = parse_filename(self.file_path)

    def get_chunk(self, band, xoff, xsize, yoff, ysize):
        """Read the band array for the requested window, NaN-masked for nodata."""
        src = _open_dataset(self.file_path)
        window = ((yoff, yoff + ysize), (xoff, xoff + xsize))
        raster_band = src.read(band, window=window).astype(np.float32)

        nodata_values = {self.nodata_from_file[band], self.nodata_from_arg}
        nodata_values.discard(None)
        if nodata_values:
            nodata_mask = np.isin(raster_band, list(nodata_values))
            raster_band[nodata_mask] = np.nan

        return raster_band

    def get_chunk_in_wrapper(self, band, xc, xc_size, yc, yc_size):
        """Get the image band fitted into the wrapper grid for the requested chunk."""
        xc_max = xc + xc_size
        yc_max = yc + yc_size

        # chunk fully outside the image footprint
        if xc_max <= self.xi_min or xc >= self.xi_max or yc_max <= self.yi_min or yc >= self.yi_max:
            return None

        # intersect chunk window with image window in wrapper coords
        x0 = max(xc, self.xi_min)
        x1 = min(xc_max, self.xi_max)
        y0 = max(yc, self.yi_min)
        y1 = min(yc_max, self.yi_max)

        xoff = x0 - self.xi_min
        yoff = y0 - self.yi_min
        xsize = x1 - x0
        ysize = y1 - y0

        x_min = x0 - xc
        y_min = y0 - yc

        chunk_matrix = np.full((yc_size, xc_size), np.nan, dtype=np.float32)
        data_chunk = self.get_chunk(band, xoff, xsize, yoff, ysize)

        # Edge case: rasterio may return a slightly smaller/larger array near the
        # raster boundary; pad with NaN or crop to fit the target slice.
        target = chunk_matrix[y_min:y_min + ysize, x_min:x_min + xsize]
        if data_chunk.shape != target.shape:
            diff_y = target.shape[0] - data_chunk.shape[0]
            diff_x = target.shape[1] - data_chunk.shape[1]
            if diff_y > 0 or diff_x > 0:
                data_chunk = np.pad(
                    data_chunk,
                    ((0, max(diff_y, 0)), (0, max(diff_x, 0))),
                    mode="constant",
                    constant_values=np.nan,
                )
            if diff_y < 0 or diff_x < 0:
                data_chunk = data_chunk[: target.shape[0], : target.shape[1]]

        chunk_matrix[y_min:y_min + ysize, x_min:x_min + xsize] = data_chunk
        return chunk_matrix
