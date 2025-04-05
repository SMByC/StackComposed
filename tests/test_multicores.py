import numpy as np
import pytest
import rasterio

from stack_composed.stack_composed_main import run


@pytest.mark.parametrize("num_process", [1, 4, 6])
def test_multicores(setup_stack_composed, num_process):
    # Unpack the fixture
    preproc, band, nodata, output_type, _, chunksize, output_file, start_date, end_date, images = setup_stack_composed
    expected_file = "data/stack_composed_mean_band1.tif"

    # Run the function with the given number of processes
    run("mean", preproc, band, nodata, output_file, output_type, num_process, chunksize, start_date, end_date, images)

    # Load and compare results
    with rasterio.open(expected_file) as src:
        expected_result = src.read(1)

    with rasterio.open(output_file) as src:
        actual_result = src.read(1)

    # Assert results are equal
    np.testing.assert_array_almost_equal(actual_result, expected_result)