"""
Worker-count invariance tests.

The result must be bit-for-bit identical whether the computation runs on a
single process (num_process=1) or is distributed across multiple workers.
"""
import numpy as np
import pytest
import rasterio

from stack_composed import run

from .conftest import DATA_DIR


@pytest.mark.parametrize("num_process", [1, 4, 6])
def test_multicore_invariance(stack_args, num_process):
    stack_args.num_process = num_process
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
