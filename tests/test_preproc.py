import numpy as np
import pytest
import rasterio

from stack_composed.stack_composed_main import run


@pytest.mark.parametrize(
    "preproc,expected_file",
    [
        (">3", "data/stack_composed_preproc_1_band1.tif"),
        (">1 and <5", "data/stack_composed_preproc_2_band1.tif"),
    ]
)
def test_preproc(setup_stack_composed, preproc, expected_file):
    # Unpack the fixture
    _, band, nodata, output_type, num_process, chunksize, output_file, start_date, end_date, images = setup_stack_composed

    # preprare preproc
    def split_condition(str_cond):
        str_cond = str_cond.strip().replace(" ", "")
        if str_cond[1] == "=":
            return [str_cond[0:2], float(str_cond[2::])]
        else:
            return [str_cond[0:1], float(str_cond[1::])]

    if "and" in preproc:
        conditions = [split_condition(str_cond) for str_cond in preproc.split("and")]
    else:
        conditions = [split_condition(preproc)]

    # Run the function with the given preproc
    run("sum", conditions, band, nodata, output_file, output_type, num_process, chunksize, start_date, end_date, images)

    # Load and compare results
    with rasterio.open(expected_file) as src:
        expected_result = src.read(1)

    with rasterio.open(output_file) as src:
        actual_result = src.read(1)

    # Assert results are equal
    np.testing.assert_array_almost_equal(actual_result, expected_result)
