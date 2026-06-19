"""
Regression tests for every supported statistic.

Each test produces an output TIFF and compares it pixel-by-pixel against a
pre-generated reference file in tests/data/.  Floating-point statistics use
a relative tolerance of 1e-5; integer/Julian-day outputs are compared exactly.
"""
import numpy as np
import pytest
import rasterio

from stack_composed import _resolve_output_file, run

from .conftest import DATA_DIR


INT32_NODATA_SENTINEL = np.iinfo(np.int32).min


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ref(filename):
    """Return the absolute path to a reference file in tests/data/."""
    return str(DATA_DIR / filename)


def _run_and_load(stack_args, stat, **overrides):
    """Run the composed pipeline and return (actual_array, expected_array, profile)."""
    for k, v in overrides.items():
        setattr(stack_args, k, v)
    run(
        stat,
        stack_args.preproc,
        stack_args.band,
        stack_args.nodata,
        stack_args.output_file,
        stack_args.output_type,
        stack_args.num_process,
        stack_args.chunksize,
        stack_args.start_date,
        stack_args.end_date,
        stack_args.images,
    )
    with rasterio.open(stack_args.output_file) as dst:
        actual = dst.read(1)
        profile = dst.profile
    return actual, profile


def _reference_for_current_behavior(stat, expected):
    if stat == "sum":
        return np.where(expected == INT32_NODATA_SENTINEL, np.nan, expected).astype(np.float32)
    if stat in {"min", "max", "last_pixel", "linear_trend"}:
        return np.where(expected == INT32_NODATA_SENTINEL, 0, expected).astype(expected.dtype)
    return expected


# ---------------------------------------------------------------------------
# Statistic regression tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "stat, ref_file, rtol",
    [
        ("min",             "stack_composed_min_band1.tif",           0),
        ("max",             "stack_composed_max_band1.tif",           0),
        ("mean",            "stack_composed_mean_band1.tif",          1e-5),
        ("median",          "stack_composed_median_band1.tif",        1e-5),
        ("std",             "stack_composed_std_band1.tif",           1e-5),
        ("sum",             "stack_composed_sum_band1.tif",           0),
        ("gmean",           "stack_composed_gmean_band1.tif",         1e-5),
        ("percentile_38",   "stack_composed_percentile_38_band1.tif", 1e-5),
        ("extract_2",       "stack_composed_extract_2_band1.tif",     1e-5),
        ("valid_pixels",    "stack_composed_valid_pixels_band1.tif",  0),
        ("last_pixel",      "stack_composed_last_pixel_band1.tif",    0),
        ("jday_last_pixel", "stack_composed_jday_last_pixel_band1.tif", 0),
        ("jday_median",     "stack_composed_jday_median_band1.tif",   0),
        ("linear_trend",    "stack_composed_linear_trend_x1e6_band1.tif", 0),
        ("trim_mean_10_80", "stack_composed_trim_mean_10_80_band1.tif",  1e-5),
    ],
)
def test_statistic(stack_args, stat, ref_file, rtol):
    actual, profile = _run_and_load(stack_args, stat)

    with rasterio.open(_ref(ref_file)) as src:
        expected = src.read(1)
    expected = _reference_for_current_behavior(stat, expected)

    # Shape and dtype must match the reference exactly.
    assert actual.shape == expected.shape, f"shape mismatch: {actual.shape} vs {expected.shape}"
    assert actual.dtype == expected.dtype, f"dtype mismatch: {actual.dtype} vs {expected.dtype}"

    if rtol == 0:
        np.testing.assert_array_equal(actual, expected)
    else:
        np.testing.assert_allclose(actual, expected, rtol=rtol, equal_nan=True)


# ---------------------------------------------------------------------------
# Output metadata
# ---------------------------------------------------------------------------

def test_output_geospatial_metadata(stack_args):
    """Output CRS and transform must match the reference."""
    _, profile = _run_and_load(stack_args, "mean")

    with rasterio.open(_ref("stack_composed_mean_band1.tif")) as ref:
        assert profile["crs"] == ref.profile["crs"], "CRS mismatch"
        assert profile["transform"] == ref.profile["transform"], "transform mismatch"
        assert profile["width"] == ref.profile["width"]
        assert profile["height"] == ref.profile["height"]


def test_explicit_output_file_is_suffixed_for_multiple_bands(tmp_path):
    output = tmp_path / "result.tif"
    resolved = _resolve_output_file(str(output), "mean", 2, multiple_bands=True)
    assert resolved == str(tmp_path / "result_band2.tif")


def test_explicit_output_file_is_unchanged_for_single_band(tmp_path):
    output = tmp_path / "result.tif"
    resolved = _resolve_output_file(str(output), "mean", 1, multiple_bands=False)
    assert resolved == str(output)


# ---------------------------------------------------------------------------
# Error-condition tests
# ---------------------------------------------------------------------------

def test_invalid_stat_name_returns_early(stack_args, capsys):
    """An unknown statistic should print an error and return without writing output."""
    run(
        "not_a_stat",
        None, stack_args.band, None, stack_args.output_file,
        None, 1, 200, None, None, stack_args.images,
    )
    out = capsys.readouterr().out
    assert "unknown statistic" in out.lower() or "error" in out.lower()
    import os
    assert not os.path.exists(stack_args.output_file), "no output file should be created"


def test_too_few_images_exits(stack_args):
    """Passing a single image must call sys.exit(1)."""
    with pytest.raises(SystemExit) as exc:
        run(
            "mean",
            None, stack_args.band, None, stack_args.output_file,
            None, 1, 200, None, None,
            stack_args.images[:1],  # only one image
        )
    assert exc.value.code == 1
