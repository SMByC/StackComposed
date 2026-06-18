#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Stack Composed
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
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds

from core import header
from core.image import Image
from core.stats import statistic

IMAGE_EXTENSIONS = (".tif", ".img", ".hdr")
_CONDITION_OPERATORS = frozenset(("<", "<=", ">", ">=", "==", "!="))

_FIXED_STATS = frozenset({
    "median", "mean", "gmean", "sum", "max", "min", "std",
    "valid_pixels", "last_pixel", "jday_last_pixel", "jday_median", "linear_trend",
})
_PREFIX_STATS = ("extract_", "percentile_", "trim_mean_")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_stat(stat):
    """Validate the requested statistic name; print an error and return False on failure."""
    if stat in _FIXED_STATS:
        return True

    if stat.startswith("extract_"):
        parts = stat.split("_")
        try:
            if len(parts) != 2:
                raise ValueError
            int(parts[1])
        except ValueError:
            print(f"\nError: invalid statistic '{stat}'.")
            print("  extract_NN requires one integer value, e.g. extract_2")
            return False
        return True

    if stat.startswith("percentile_"):
        parts = stat.split("_")
        try:
            if len(parts) != 2:
                raise ValueError
            percentile = int(parts[1])
            if not 0 <= percentile <= 100:
                raise ValueError
        except ValueError:
            print(f"\nError: invalid statistic '{stat}'.")
            print("  percentile_NN requires one integer percentile in [0, 100], e.g. percentile_25")
            return False
        return True

    if stat.startswith("trim_mean_"):
        parts = stat.split("_")
        try:
            if len(parts) != 4:
                raise ValueError
            lower = int(parts[2])
            upper = int(parts[3])
            if not 0 <= lower <= upper <= 100:
                raise ValueError
        except ValueError:
            print(f"\nError: invalid statistic '{stat}'.")
            print("  trim_mean_LL_UL requires bounds in [0, 100] with LL <= UL, e.g. trim_mean_10_90")
            return False
        return True

    print(f"\nError: unknown statistic '{stat}'.")
    print(
        "  Available statistics: extract_NN, median, mean, gmean, sum, max, min, std,\n"
        "  valid_pixels, last_pixel, jday_last_pixel, jday_median, linear_trend,\n"
        "  percentile_NN, trim_mean_LL_UL\n"
        "  Run with '-h' for descriptions of each statistic."
    )
    return False


def _collect_image_files(inputs):
    """Recursively gather supported raster files from paths or directories."""
    files = []
    for entry in inputs:
        entry_path = Path(entry)
        if entry_path.is_file():
            if entry_path.suffix.lower() in IMAGE_EXTENSIONS:
                files.append(str(entry_path.resolve()))
        elif entry_path.is_dir():
            for found in sorted(entry_path.rglob("*")):
                if found.is_file() and found.suffix.lower() in IMAGE_EXTENSIONS:
                    files.append(str(found.resolve()))
    return files


def _resolve_output_file(output, stat, band, multiple_bands=False):
    """Return the output file path for a band, or None if the path is invalid."""
    output_path = Path(output)
    if output_path.is_dir():
        path = output_path / f"stack_composed_{stat}_band{band}.tif"
    elif output_path.suffix.lower() == ".tif":
        if output_path.parent.exists() or str(output_path.parent) == ".":
            path = output_path if output_path.is_absolute() else Path.cwd() / output_path
            if multiple_bands:
                path = path.with_name(f"{path.stem}_band{band}{path.suffix}")
        else:
            return None
    else:
        return None

    if stat == "linear_trend":
        path = path.with_name(path.name.replace("linear_trend_band", "linear_trend_x1e6_band"))
    return str(path)


def _resolve_output_type(stat, output_type, images, band, nimages):
    """Return the output dtype, falling back to sensible defaults per statistic."""
    if output_type is not None:
        return output_type
    dtypes = {img.data_type[band] for img in images}
    data_type = next(iter(dtypes))
    if stat in {"max", "min", "last_pixel"}:
        return data_type
    if stat == "sum":
        # Default to float to avoid integer overflow when summing many images
        return np.float64 if data_type == "float64" else np.float32
    if stat in {"jday_last_pixel", "jday_median"}:
        return np.uint16
    if stat in {"median", "mean", "gmean", "std", "snr"} or stat.startswith(_PREFIX_STATS):
        return np.float64 if data_type == "float64" else np.float32
    if stat == "valid_pixels":
        return np.uint8 if nimages < 256 else np.uint16
    if stat == "linear_trend":
        return np.int32
    return np.float32


def _resolve_output_nodata(nodata, images, band):
    """Return the nodata value to embed in the output file."""
    if nodata is not None:
        return nodata
    nodata_from_file = {img.nodata_from_file[band] for img in images}
    if len(nodata_from_file) == 1 and None not in nodata_from_file:
        return nodata_from_file.pop()
    if None not in nodata_from_file:
        print(
            "\nWarning: input images have different nodata values; "
            "no nodata will be written to the output file."
        )
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(stat, preproc, bands, nodata, output, output_type, num_process, chunksize,
        start_date, end_date, inputs):
    """Compute the stack-composed statistic and write the result to a GeoTIFF.

    Parameters
    ----------
    stat:         name of the statistic (see ``_FIXED_STATS`` / ``_PREFIX_STATS``).
    preproc:      preprocessing spec (float threshold, condition list, or string).
    bands:        int, comma-separated string, or list of band numbers to process.
    nodata:       pixel value to treat as nodata in the inputs (overrides file metadata).
    output:       output directory or explicit ``.tif`` filename.
    output_type:  numpy dtype string for the output (None = auto-select).
    num_process:  number of parallel worker processes.
    chunksize:    tile size (in pixels) used to divide the work.
    start_date:   earliest date to include (``datetime.date``); requires filename metadata.
    end_date:     latest  date to include (``datetime.date``); requires filename metadata.
    inputs:       list of file paths or directory paths to search for images.
    """
    print(header)

    if not _validate_stat(stat):
        return

    if num_process < 1:
        print("\nError: -p/num_process must be at least 1.")
        sys.exit(1)
    if chunksize < 1:
        print("\nError: -chunks/chunksize must be at least 1 pixel.")
        sys.exit(1)

    print("\nLoading and preparing images:", flush=True)
    images_files = _collect_image_files(inputs)

    Image.wrapper_extent = None
    Image.wrapper_x_res = None
    Image.wrapper_y_res = None
    Image.wrapper_shape = None
    Image.projection = None

    # Normalise the bands argument to a list of ints.
    if isinstance(bands, int):
        bands = [bands]
    elif not isinstance(bands, list):
        try:
            bands = [int(b) for b in bands.split(",")]
        except ValueError:
            print(f"\nError: invalid -bands value '{bands}'. Use integers like 1 or 1,2,3.")
            sys.exit(1)

    multiple_bands = len(bands) > 1
    images = [Image(img) for img in images_files]

    # Optional date-range filter (requires date metadata embedded in filenames).
    if start_date is not None or end_date is not None:
        for image in images:
            image.set_metadata_from_filename()
        if start_date is not None:
            images = [img for img in images if img.date >= start_date]
        if end_date is not None:
            images = [img for img in images if img.date <= end_date]

    if len(images) <= 1:
        print(
            f"\nError: found {len(images)} image(s) after loading"
            + (" and date filtering" if start_date or end_date else "")
            + "; at least 2 images are required."
        )
        sys.exit(1)

    for image in images:
        image.nodata_from_arg = nodata

    min_x = min(img.extent[0] for img in images)
    max_y = max(img.extent[1] for img in images)
    max_x = max(img.extent[2] for img in images)
    min_y = min(img.extent[3] for img in images)
    wrapper_extent = [min_x, max_y, max_x, min_y]
    wrapper_x_res = images[0].x_res
    wrapper_y_res = images[0].y_res
    wrapper_shape = (
        int((max_y - min_y) / wrapper_y_res),
        int((max_x - min_x) / wrapper_x_res),
    )
    Image.wrapper_extent = wrapper_extent
    Image.wrapper_x_res = wrapper_x_res
    Image.wrapper_y_res = wrapper_y_res
    Image.wrapper_shape = wrapper_shape
    projection = Image.projection

    chunksize = min(chunksize, min(wrapper_shape))

    if len(images_files) != len(images):
        print(f"  images found:      {len(images_files)}")
        print(f"  images to process: {len(images)} (after date filter)")
    else:
        print(f"  images to process: {len(images)}")
    print(f"  band(s):           {', '.join(str(b) for b in bands)}")
    print(f"  pixel size:        {round(wrapper_x_res, 1)} × {round(wrapper_y_res, 1)} m")
    print(f"  wrapper extent:    {wrapper_shape[1]} × {wrapper_shape[0]} pixels")
    print(f"  workers / chunks:  {num_process} cores, {chunksize} px tiles")

    print("  checking bands and pixel size … ", flush=True, end="")
    for image in images:
        for band in bands:
            if band > image.n_bands:
                print(
                    f"\n\nError: '{Path(image.file_path).name}' has only {image.n_bands} "
                    f"band(s); band {band} does not exist.\n"
                )
                sys.exit(1)
        if (round(image.x_res, 1) != round(wrapper_x_res, 1)
                or round(image.y_res, 1) != round(wrapper_y_res, 1)):
            print(
                f"\n\nError: '{Path(image.file_path).name}' has pixel size "
                f"{round(image.x_res, 1)} × {round(image.y_res, 1)} m, "
                f"but the reference is "
                f"{round(wrapper_x_res, 1)} × {round(wrapper_y_res, 1)} m. "
                "All images must share the same pixel size.\n"
            )
            sys.exit(1)
    print("OK")

    for image in images:
        image.set_bounds()

    if stat in {"last_pixel", "jday_last_pixel", "jday_median", "linear_trend"}:
        for image in images:
            image.set_metadata_from_filename()

    for band in bands:
        output_file = _resolve_output_file(output, stat, band, multiple_bands)
        if output_file is None:
            print(
                f"\nError: cannot resolve output path '{output}'.\n"
                "  Provide an existing directory, or a path ending in '.tif' whose "
                "parent directory exists."
            )
            sys.exit(1)

        resolved_dtype = _resolve_output_type(stat, output_type, images, band, len(images))
        output_nodata_value = _resolve_output_nodata(nodata, images, band)

        profile = {
            "driver": "GTiff",
            "dtype": resolved_dtype,
            "height": wrapper_shape[0],
            "width": wrapper_shape[1],
            "count": 1,
            "BIGTIFF": "IF_NEEDED",
            "nodata": output_nodata_value,
            "crs": projection,
            "transform": from_bounds(
                wrapper_extent[0], wrapper_extent[3],
                wrapper_extent[2], wrapper_extent[1],
                wrapper_shape[1], wrapper_shape[0],
            ),
        }

        with rasterio.open(output_file, "w+", **profile):
            pass

        print(f"\nProcessing '{stat}' — band {band}:")
        statistic(stat, preproc, images, band, num_process, chunksize, output_file)
        print(f"  → saved to {output_file}")

    print("\nDone.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cli(argv=None):
    """Command-line entry point."""
    import argparse
    import resource

    # Mirror the ulimits set by the legacy bin/stack-composed wrapper:
    # raise open-file limit (many raster files) and remove stack size cap.
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
        resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    except (ValueError, resource.error):
        pass
    from datetime import datetime
    from multiprocessing import cpu_count

    from core import epilog

    parser = argparse.ArgumentParser(
        prog="stack-composed",
        description=(
            "Compute a per-pixel statistic over a stack of georeferenced raster images\n"
            "that may span different tiles or extents. Results are written to a single\n"
            "GeoTIFF covering the union of all input extents."
        ),
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    def date_validator(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            raise argparse.ArgumentTypeError(f"'{s}' is not a valid date — expected YYYY-MM-DD")

    def _split_condition(str_cond):
        str_cond = str_cond.strip().replace(" ", "")
        if not str_cond:
            raise ValueError
        if len(str_cond) > 1 and str_cond[1] == "=":
            op = str_cond[0:2]
            value = str_cond[2:]
        else:
            op = str_cond[0:1]
            value = str_cond[1:]
        if op not in _CONDITION_OPERATORS:
            raise ValueError
        return [op, float(value)]

    def _validate_percentile_pair(value, label):
        parts = value.split("_")
        try:
            lower = int(parts[1])
            upper = int(parts[2])
            if len(parts) != 3 or not 0 <= lower <= upper <= 100:
                raise ValueError
            return value
        except (IndexError, ValueError):
            raise argparse.ArgumentTypeError(
                f"'{value}' — {label} expects integer bounds in [0, 100] with LL <= UL, "
                f"e.g. {label.lower().replace('ll_ul', '10_90')}"
            )

    def preproc_validator(preproc):
        # Plain numeric threshold: pixels below/equal to this value are excluded.
        try:
            return float(preproc)
        except ValueError:
            pass

        if preproc.startswith("percentile_"):
            return _validate_percentile_pair(preproc, "percentile_LL_UL")

        if preproc.endswith("_std_devs"):
            try:
                float(preproc.split("_")[0])
                return preproc
            except (IndexError, ValueError):
                raise argparse.ArgumentTypeError(
                    f"'{preproc}' — NN_std_devs expects a numeric multiplier, "
                    "e.g. 2.5_std_devs"
                )

        if preproc.endswith("_IQR"):
            try:
                float(preproc.split("_")[0])
                return preproc
            except (IndexError, ValueError):
                raise argparse.ArgumentTypeError(
                    f"'{preproc}' — NN_IQR expects a numeric multiplier, e.g. 1.5_IQR"
                )

        try:
            if "and" in preproc:
                return [_split_condition(s) for s in preproc.split("and")]
            return [_split_condition(preproc)]
        except Exception:
            raise argparse.ArgumentTypeError(
                f"'{preproc}' is not a valid preprocessing expression.\n"
                "  Examples: '>3', '>=1 and <=5'"
            )

    parser.add_argument(
        "-stat", type=str, required=True,
        metavar="STAT",
        help=(
            "Statistic to compute over the pixel stack along the Z-axis.\n"
            "Fixed: median, mean, gmean, sum, max, min, std, valid_pixels,\n"
            "       last_pixel, jday_last_pixel, jday_median, linear_trend\n"
            "Parameterised: extract_NN, percentile_NN, trim_mean_LL_UL\n"
            "Run with '-h' for detailed descriptions."
        ),
    )
    parser.add_argument(
        "-preproc", type=preproc_validator, dest="preproc", default=None,
        metavar="EXPR",
        help=(
            "Optional preprocessing expression applied before computing the statistic.\n"
            "Pixels that do not satisfy the condition are treated as nodata.\n"
            "Examples:\n"
            "  '>3'              keep pixels greater than 3\n"
            "  '>=1 and <=5'    keep pixels in the range [1, 5]\n"
            "  'percentile_10_90'  keep values in the 10th–90th percentile\n"
            "  '2.5_std_devs'   keep within 2.5 standard deviations of the mean\n"
            "  '1.5_IQR'        keep within 1.5 × IQR of the median"
        ),
    )
    parser.add_argument(
        "-bands", type=str, required=True,
        metavar="BANDS",
        help="Band number(s) to process, comma-separated (e.g. 1 or 1,2,3).",
    )
    parser.add_argument(
        "-nodata", type=float, default=None,
        metavar="VALUE",
        help=(
            "Pixel value to treat as nodata in the input images.\n"
            "Overrides any nodata value embedded in the file metadata."
        ),
    )
    parser.add_argument(
        "-o", type=str, dest="output", default=os.getcwd(),
        metavar="PATH",
        help=(
            "Output location. Either:\n"
            "  • an existing directory (auto-names the file), or\n"
            "  • an explicit .tif filename whose parent directory exists.\n"
            "Default: current working directory."
        ),
    )
    parser.add_argument(
        "-ot", type=str, dest="output_type", default=None,
        metavar="DTYPE",
        choices=("int8", "uint16", "uint32", "int16", "int32", "float32", "float64"),
        help=(
            "Force a specific output data type. When omitted, a suitable type\n"
            "is chosen automatically based on the statistic and input types."
        ),
    )
    parser.add_argument(
        "-p", type=int, default=max(cpu_count() - 1, 1),
        metavar="N",
        help=(
            f"Number of parallel worker processes (default: {max(cpu_count() - 1, 1)}, "
            "i.e. all cores minus one).\n"
            "Use -p 1 to disable parallel processing."
        ),
    )
    parser.add_argument(
        "-chunks", type=int, default=1000,
        metavar="PX",
        help=(
            "Tile size in pixels used to divide the work across workers\n"
            "(default: 1000). Larger tiles use more memory per worker;\n"
            "smaller tiles reduce memory but increase scheduling overhead."
        ),
    )
    parser.add_argument(
        "-start", type=date_validator, dest="start_date",
        metavar="YYYY-MM-DD",
        help="Include only images on or after this date (requires Landsat-style filenames).",
    )
    parser.add_argument(
        "-end", type=date_validator, dest="end_date",
        metavar="YYYY-MM-DD",
        help="Include only images on or before this date (requires Landsat-style filenames).",
    )
    parser.add_argument(
        "inputs", type=str, nargs="*",
        metavar="INPUT",
        help="Input image files (.tif/.img/.hdr) or directories to search recursively.",
    )

    args = parser.parse_args(argv)

    run(
        args.stat, args.preproc, args.bands, args.nodata, args.output, args.output_type,
        args.p, args.chunks, args.start_date, args.end_date, args.inputs,
    )


if __name__ == "__main__":
    cli()
