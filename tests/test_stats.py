import pytest
import numpy as np
import rasterio

from stack_composed.stack_composed_main import run


@pytest.mark.parametrize(
    "stat,expected_file",
    [
        ("min", "data/stack_composed_min_band1.tif"),
        ("max", "data/stack_composed_max_band1.tif"),
        ("mean", "data/stack_composed_mean_band1.tif"),
        ("median", "data/stack_composed_median_band1.tif"),
        ("std", "data/stack_composed_std_band1.tif"),
        ("sum", "data/stack_composed_sum_band1.tif"),
        ("gmean", "data/stack_composed_gmean_band1.tif"),
        ("percentile_38", "data/stack_composed_percentile_38_band1.tif"),
        ("extract_2", "data/stack_composed_extract_2_band1.tif"),
        ("valid_pixels", "data/stack_composed_valid_pixels_band1.tif"),
        ("last_pixel", "data/stack_composed_last_pixel_band1.tif"),
        ("jday_last_pixel", "data/stack_composed_jday_last_pixel_band1.tif"),
        ("jday_median", "data/stack_composed_jday_median_band1.tif"),
    ]
)
def test_statistic_operations(setup_stack_composed, stat, expected_file):
    # Unpack the fixture
    preproc, band, nodata, output_type, num_process, chunksize, output_file, start_date, end_date, images = setup_stack_composed

    # Run the function with the given statistic
    run(stat, preproc, band, nodata, output_file, output_type, num_process, chunksize, start_date, end_date, images)

    # Load and compare results
    with rasterio.open(expected_file) as src:
        expected_result = src.read(1)

    with rasterio.open(output_file) as src:
        actual_result = src.read(1)

    # Assert results are equal
    np.testing.assert_array_almost_equal(actual_result, expected_result)