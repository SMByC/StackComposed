"""
Shared fixtures for StackComposed tests.

All test data lives in tests/data/.  Fixtures expose absolute paths so tests
pass regardless of the working directory when pytest is invoked.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / "data"

IMAGES = [
    str(DATA_DIR / "Landsat_8_53_020601_7ETM_Reflec_SR_Enmask.tif"),
    str(DATA_DIR / "Landsat_8_53_020823_7ETM_Reflec_SR_Enmask.tif"),
]


@pytest.fixture(autouse=True)
def _chdir_to_tests(monkeypatch):
    """Ensure the working directory is the tests folder for the duration of each test."""
    monkeypatch.chdir(TEST_DIR)


@pytest.fixture
def stack_args(tmp_path):
    """
    Default arguments for a two-image stack-composed run.

    Tests can override individual fields from the returned SimpleNamespace:
        args = stack_args; args.num_process = 1
    """
    return SimpleNamespace(
        images=IMAGES,
        band=1,
        preproc=None,
        nodata=None,
        output_type=None,
        num_process=4,
        chunksize=200,
        start_date=None,
        end_date=None,
        output_file=str(tmp_path / "output.tif"),
    )
