"""
Unit tests for core/parse.py.

parse.py is pure Python (no rasterio), so these tests run fast and cover all
three filename formats plus the dispatch function and error paths.
"""
import datetime

import pytest

from core.parse import (
    calc_date,
    parse_filename,
    parse_landsat_ID_newFilename,
    parse_landsat_ID_oldFilename,
    parse_SMBYC_filename,
)


# ---------------------------------------------------------------------------
# calc_date
# ---------------------------------------------------------------------------

def test_calc_date_first_day_of_year():
    assert calc_date(2020, 1) == datetime.date(2020, 1, 1)


def test_calc_date_last_day_of_year():
    assert calc_date(2020, 366) == datetime.date(2020, 12, 31)  # 2020 is a leap year


def test_calc_date_mid_year():
    assert calc_date(2016, 320) == datetime.date(2016, 11, 15)


# ---------------------------------------------------------------------------
# Old Landsat filename (LCxxxx…)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "LC80070592016320LGN00_band1.tif",
            (8, "OLI", 7, 59, datetime.date(2016, 11, 15), 320),
        ),
        (
            "LE70070592003123LGN00_band1.tif",
            (7, "ETM", 7, 59, datetime.date(2003, 5, 3), 123),
        ),
        (
            "LT50070592000100LGN00_band1.tif",
            (5, "TM", 7, 59, datetime.date(2000, 4, 9), 100),
        ),
    ],
)
def test_parse_old_filename(filename, expected):
    result = parse_landsat_ID_oldFilename(filename)
    assert result == expected


def test_parse_old_filename_unknown_sensor():
    with pytest.raises((ValueError, Exception)):
        parse_landsat_ID_oldFilename("LZ80070592016320LGN00_band1.tif")


# ---------------------------------------------------------------------------
# New ESPA Landsat filename (LC08_…)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "LC08_L1TP_007059_20161115_20170318_01_T2_b1.tif",
            (8, "OLI", 7, 59, datetime.date(2016, 11, 15), 320),
        ),
        (
            "LE07_L1TP_007059_20030503_20160928_01_T1_b1.tif",
            (7, "ETM", 7, 59, datetime.date(2003, 5, 3), 123),
        ),
    ],
)
def test_parse_new_filename(filename, expected):
    version, sensor, path, row, date, jday = parse_landsat_ID_newFilename(filename)
    exp_version, exp_sensor, exp_path, exp_row, exp_date, exp_jday = expected
    assert version == exp_version
    assert sensor == exp_sensor
    assert path == exp_path
    assert row == exp_row
    assert date == exp_date
    assert jday == exp_jday


# ---------------------------------------------------------------------------
# SMBYC filename (Landsat_…)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "Landsat_8_53_020601_7ETM_Reflec_SR_Enmask.tif",
            (7, "ETM", 8, 53, datetime.date(2002, 6, 1), 152),
        ),
        (
            "Landsat_8_53_020823_7ETM_Reflec_SR_Enmask.tif",
            (7, "ETM", 8, 53, datetime.date(2002, 8, 23), 235),
        ),
    ],
)
def test_parse_smbyc_filename(filename, expected):
    result = parse_SMBYC_filename(filename)
    assert result == expected


# ---------------------------------------------------------------------------
# parse_filename dispatch
# ---------------------------------------------------------------------------

def test_dispatch_smbyc():
    result = parse_filename("Landsat_8_53_020601_7ETM_Reflec_SR_Enmask.tif")
    assert result[4] == datetime.date(2002, 6, 1)


def test_dispatch_new_espa():
    result = parse_filename("LC08_L1TP_007059_20161115_20170318_01_T2_b1.tif")
    assert result[4] == datetime.date(2016, 11, 15)


def test_dispatch_old_landsat():
    result = parse_filename("LC80070592016320LGN00_band1.tif")
    assert result[4] == datetime.date(2016, 11, 15)


def test_dispatch_bad_filename_raises():
    with pytest.raises(Exception, match="Cannot parse filename"):
        parse_filename("not_a_landsat_file_at_all.tif")
