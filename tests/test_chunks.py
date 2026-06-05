"""
Chunk-size invariance tests.

The result of a computation must be identical regardless of how the wrapper
extent is tiled.  chunksize=500 on a 302×211-pixel wrapper produces a single
tile (tests the un-tiled path); smaller values exercise the tiling logic and
edge handling at tile borders.
"""
import numpy as np
import pytest
import rasterio

from stack_composed import run

from .conftest import DATA_DIR


@pytest.mark.parametrize("chunksize", [10, 50, 100, 200, 500])
def test_chunksize_invariance(stack_args, chunksize):
    stack_args.chunksize = chunksize
    run(
        "mean",
        stack_args.preproc, stack_args.band, stack_args.nodata, stack_args.output_file,
        stack_args.output_type, stack_args.num_process, stack_args.chunksize,
        stack_args.start_date, stack_args.end_date, stack_args.images,
    )
    with rasterio.open(stack_args.output_file) as dst:
        actual = dst.read(1)
    with rasterio.open(DATA_DIR / "stack_composed_mean_band1.tif") as ref:
        expected = ref.read(1)

    np.testing.assert_allclose(actual, expected, rtol=1e-5, equal_nan=True)
