import pytest
from pathlib import Path


@pytest.fixture
def setup_stack_composed(tmp_path):
    band = 1
    num_process = 4
    chunksize = 200
    preproc = None
    nodata = None
    output_type = None
    start_date = None
    end_date = None
    # List of image file paths
    images = ["Landsat_8_53_020601_7ETM_Reflec_SR_Enmask.tif", "Landsat_8_53_020823_7ETM_Reflec_SR_Enmask.tif"]
    images = [str("data" / Path(image)) for image in images]
    output_file = str(tmp_path / 'test_output.tif')

    return preproc, band, nodata, output_type, num_process, chunksize, output_file, start_date, end_date, images