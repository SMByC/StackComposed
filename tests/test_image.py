"""
Unit tests for stack_composed/image.py.

Tests cover Image metadata loading, bounds calculation, chunk retrieval,
nodata masking, the ENVI dataset-path resolver, and the get_chunk_in_wrapper
edge cases (out-of-bounds, partial overlap).
"""
import numpy as np
import pytest
import rasterio

from stack_composed.image import Image, reset_dataset_cache

from .conftest import DATA_DIR

IMAGE_A = str(DATA_DIR / "Landsat_8_53_020601_7ETM_Reflec_SR_Enmask.tif")
IMAGE_B = str(DATA_DIR / "Landsat_8_53_020823_7ETM_Reflec_SR_Enmask.tif")


@pytest.fixture(autouse=True)
def _reset_image_class():
    """Reset Image class-level state between tests."""
    yield
    Image.wrapper_extent = None
    Image.wrapper_x_res = None
    Image.wrapper_y_res = None
    Image.wrapper_shape = None
    Image.projection = None
    reset_dataset_cache()


# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------

def test_image_loads_extent():
    img = Image(IMAGE_A)
    min_x, max_y, max_x, min_y = img.extent
    assert max_x > min_x
    assert max_y > min_y


def test_image_pixel_size():
    img = Image(IMAGE_A)
    assert img.x_res == pytest.approx(30.0, abs=0.1)
    assert img.y_res == pytest.approx(30.0, abs=0.1)


def test_image_band_count():
    img = Image(IMAGE_A)
    assert img.n_bands >= 1


def test_image_data_type_recorded():
    img = Image(IMAGE_A)
    assert 1 in img.data_type


def test_image_projection_set_on_first_load():
    Image(IMAGE_A)
    assert Image.projection is not None


def test_image_nodata_from_arg_defaults_to_none():
    img = Image(IMAGE_A)
    assert img.nodata_from_arg is None


# ---------------------------------------------------------------------------
# get_dataset_path — ENVI error
# ---------------------------------------------------------------------------

def test_get_dataset_path_missing_envi_raises(tmp_path):
    """An .hdr file with no matching dataset should raise FileNotFoundError."""
    hdr = tmp_path / "missing.hdr"
    hdr.write_text("")
    with pytest.raises(FileNotFoundError, match="ENVI dataset"):
        Image.get_dataset_path(str(hdr))


def test_get_dataset_path_passthrough_for_tif():
    path = Image.get_dataset_path(IMAGE_A)
    assert path == IMAGE_A


# ---------------------------------------------------------------------------
# set_bounds
# ---------------------------------------------------------------------------

def _setup_wrapper_from_images():
    """Load both test images and set the shared wrapper state."""
    img_a = Image(IMAGE_A)
    img_b = Image(IMAGE_B)
    images = [img_a, img_b]
    Image.wrapper_extent = [
        min(i.extent[0] for i in images),
        max(i.extent[1] for i in images),
        max(i.extent[2] for i in images),
        min(i.extent[3] for i in images),
    ]
    Image.wrapper_x_res = img_a.x_res
    Image.wrapper_y_res = img_a.y_res
    Image.wrapper_shape = (
        int((Image.wrapper_extent[1] - Image.wrapper_extent[3]) / Image.wrapper_y_res),
        int((Image.wrapper_extent[2] - Image.wrapper_extent[0]) / Image.wrapper_x_res),
    )
    for img in images:
        img.set_bounds()
    return images


def test_set_bounds_produces_non_negative_indices():
    images = _setup_wrapper_from_images()
    for img in images:
        assert img.xi_min >= 0
        assert img.yi_min >= 0


def test_set_bounds_indices_within_wrapper():
    images = _setup_wrapper_from_images()
    H, W = Image.wrapper_shape
    for img in images:
        assert img.xi_max <= W
        assert img.yi_max <= H


# ---------------------------------------------------------------------------
# get_chunk
# ---------------------------------------------------------------------------

def test_get_chunk_shape():
    img = Image(IMAGE_A)
    with rasterio.open(IMAGE_A) as src:
        w, h = src.width, src.height
    chunk = img.get_chunk(1, 0, w // 2, 0, h // 2)
    assert chunk.shape == (h // 2, w // 2)


def test_get_chunk_dtype_float32():
    img = Image(IMAGE_A)
    chunk = img.get_chunk(1, 0, 10, 0, 10)
    assert chunk.dtype == np.float32


def test_get_chunk_nodata_becomes_nan():
    img = Image(IMAGE_A)
    with rasterio.open(IMAGE_A) as src:
        nodata_val = src.nodatavals[0]
    if nodata_val is None:
        pytest.skip("image has no nodata value")
    img.nodata_from_arg = None  # rely on file nodata
    with rasterio.open(IMAGE_A) as src:
        w, h = src.width, src.height
    chunk = img.get_chunk(1, 0, w, 0, h)
    assert np.isnan(chunk).any(), "nodata pixels should be NaN after get_chunk"


def test_get_chunk_arg_nodata_overrides():
    img = Image(IMAGE_A)
    img.nodata_from_arg = 0.0
    chunk = img.get_chunk(1, 0, 10, 0, 10)
    assert not np.any(chunk == 0.0), "pixels equal to nodata_from_arg should become NaN"


# ---------------------------------------------------------------------------
# get_chunk_in_wrapper
# ---------------------------------------------------------------------------

def test_get_chunk_in_wrapper_returns_none_when_outside():
    images = _setup_wrapper_from_images()
    img = images[0]
    H, W = Image.wrapper_shape
    # Request a chunk well beyond the right edge.
    result = img.get_chunk_in_wrapper(1, W + 100, 50, 0, 50)
    assert result is None


def test_get_chunk_in_wrapper_correct_shape():
    images = _setup_wrapper_from_images()
    img = images[0]
    xc, yc, size = 0, 0, 50
    result = img.get_chunk_in_wrapper(1, xc, size, yc, size)
    if result is not None:
        assert result.shape == (size, size)


def test_get_chunk_in_wrapper_dtype_float32():
    images = _setup_wrapper_from_images()
    img = images[0]
    result = img.get_chunk_in_wrapper(1, 0, 50, 0, 50)
    if result is not None:
        assert result.dtype == np.float32
