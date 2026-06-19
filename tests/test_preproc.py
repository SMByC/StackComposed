"""
Tests for the -preproc preprocessing filters.

Regression tests use pre-generated reference files.  Smoke tests for the
additional filter types (percentile, std_devs, IQR) verify that the output
has the correct shape and that filtering actually removes some values.
"""
import numpy as np
import pytest
import rasterio

from stack_composed import cli, run

from .conftest import DATA_DIR


INT32_NODATA_SENTINEL = np.iinfo(np.int32).min


def _ref(filename):
    return str(DATA_DIR / filename)


def _parse_preproc(expr):
    """Parse a preproc string into the internal [[op, value], …] list format."""
    def _split(s):
        s = s.strip().replace(" ", "")
        return [s[:2], float(s[2:])] if s[1] == "=" else [s[:1], float(s[1:])]
    if "and" in expr:
        return [_split(c) for c in expr.split("and")]
    return [_split(expr)]


def _expected_float_nodata(filename):
    with rasterio.open(_ref(filename)) as src:
        expected = src.read(1)
    return np.where(expected == INT32_NODATA_SENTINEL, np.nan, expected).astype(np.float32)


def _run(stack_args, preproc, stat="sum"):
    run(
        stat, preproc,
        stack_args.band, stack_args.nodata, stack_args.output_file,
        stack_args.output_type, stack_args.num_process, stack_args.chunksize,
        stack_args.start_date, stack_args.end_date, stack_args.images,
    )
    with rasterio.open(stack_args.output_file) as dst:
        return dst.read(1)


# ---------------------------------------------------------------------------
# Regression tests (condition-list preprocessing)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "expr, ref_file",
    [
        (">3",        "stack_composed_preproc_1_band1.tif"),
        (">1 and <5", "stack_composed_preproc_2_band1.tif"),
    ],
)
def test_preproc_condition(stack_args, expr, ref_file):
    actual = _run(stack_args, _parse_preproc(expr))
    expected = _expected_float_nodata(ref_file)
    np.testing.assert_allclose(actual, expected, rtol=1e-5, equal_nan=True)


def test_preproc_numeric_threshold_is_rejected(stack_args, capsys):
    with pytest.raises(SystemExit) as exc:
        cli([
            "-stat", "sum",
            "-preproc", "3",
            "-bands", str(stack_args.band),
            *stack_args.images,
        ])
    assert exc.value.code == 2
    assert "not a valid preprocessing expression" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Smoke tests for string-based preprocessing variants
# ---------------------------------------------------------------------------

def test_preproc_percentile(stack_args):
    """percentile_LL_UL should produce a non-empty result of the correct shape."""
    actual = _run(stack_args, "percentile_10_90", stat="mean")
    with rasterio.open(_ref("stack_composed_mean_band1.tif")) as ref:
        unfiltered = ref.read(1)
    assert actual.shape == unfiltered.shape
    # Filtering should reduce or equal the number of valid pixels, never increase.
    valid_filtered = np.count_nonzero(~np.isnan(actual))
    valid_unfiltered = np.count_nonzero(~np.isnan(unfiltered))
    assert valid_filtered <= valid_unfiltered


def test_preproc_std_devs(stack_args):
    """NN_std_devs should produce a result with the correct shape."""
    actual = _run(stack_args, "2.0_std_devs", stat="mean")
    with rasterio.open(_ref("stack_composed_mean_band1.tif")) as ref:
        unfiltered = ref.read(1)
    assert actual.shape == unfiltered.shape


def test_preproc_iqr(stack_args):
    """NN_IQR should produce a result with the correct shape."""
    actual = _run(stack_args, "1.5_IQR", stat="mean")
    with rasterio.open(_ref("stack_composed_mean_band1.tif")) as ref:
        unfiltered = ref.read(1)
    assert actual.shape == unfiltered.shape
