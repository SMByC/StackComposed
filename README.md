# StackComposed

StackComposed computes a per-pixel statistic over a stack of georeferenced raster images (e.g. a Landsat time series). Images may span different tiles or overlap partially — StackComposed assembles them into a single wrapper extent and processes all valid observations along the time axis in parallel.

Typical use case: given dozens of Landsat scenes covering an area of interest at different dates, compute the median reflectance, the date of the last cloud-free pixel, or a linear trend — all in a single command.

## Documentation

Full documentation: [https://smbyc.github.io/StackComposed](https://smbyc.github.io/StackComposed)

## Source code

[https://github.com/SMByC/StackComposed](https://github.com/SMByC/StackComposed)

## Issue tracker

Bugs, ideas, and enhancements: [https://github.com/SMByC/StackComposed/issues](https://github.com/SMByC/StackComposed/issues)

---

## Installation

Requires the following libraries:

- [NumPy](https://numpy.org)
- [Rasterio](https://rasterio.readthedocs.io)
- [Dask](https://docs.dask.org)

**Option 1 — Conda environment:**

```bash
conda install -c conda-forge numpy rasterio dask
pip install https://github.com/SMByC/StackComposed/archive/master.zip
```

**Option 2 — UV:**

Install stack-composed as a standalone tool (manages its own isolated environment):

```bash
uv tool install git+https://github.com/SMByC/StackComposed
```

Or inside a project environment:

```bash
uv pip install git+https://github.com/SMByC/StackComposed
```

**Option 3 — pip only (dependencies already installed system-wide):**

```bash
pip install git+https://github.com/SMByC/StackComposed
```

---

## Quick start

```bash
# Compute the median of band 1 across all TIFFs in a directory
stack-composed -stat median -bands 1 -o /output/dir /path/to/images/

# Mean of bands 1–3, using 8 cores and 500 px tiles
stack-composed -stat mean -bands 1,2,3 -p 8 -chunks 500 -o result.tif /images/

# Only process images between two dates (requires Landsat-style filenames)
stack-composed -stat max -bands 1 -start 2020-01-01 -end 2022-12-31 -o /out/ /images/

# Apply preprocessing: keep only pixels in the range [1, 5] before computing the sum
stack-composed -stat sum -bands 1 -preproc '>=1 and <=5' -o /out/ /images/
```

---

## Statistics (`-stat`)

| Statistic | Description |
|-----------|-------------|
| `median` | Median of valid pixel values |
| `mean` | Arithmetic mean |
| `gmean` | Geometric mean (positive values only) |
| `sum` | Sum of valid pixel values |
| `max` | Maximum value |
| `min` | Minimum value |
| `std` | Standard deviation |
| `valid_pixels` | Count of valid (non-nodata) observations |
| `last_pixel` | Value of the most recent valid pixel |
| `jday_last_pixel` | Julian day of the most recent valid pixel |
| `jday_median` | Julian day of the temporal median |
| `linear_trend` | OLS slope ×10⁶ (int32 output), requires date metadata |
| `extract_NN` | Pixels equal to integer NN (e.g. `extract_2`) |
| `percentile_NN` | NN-th percentile (e.g. `percentile_25`) |
| `trim_mean_LL_UL` | Mean after trimming the LL–UL percentile range (e.g. `trim_mean_10_90`) |

## Preprocessing (`-preproc`)

Applied before the statistic; pixels that fail the condition are treated as nodata.

| Expression | Meaning |
|------------|---------|
| `>3` | Keep pixels greater than 3 |
| `>=1 and <=5` | Keep pixels in the range [1, 5] |
| `percentile_10_90` | Keep only values between the 10th and 90th percentile |
| `2.5_std_devs` | Keep within 2.5 standard deviations of the per-pixel mean |
| `1.5_IQR` | Keep within 1.5 × IQR of the per-pixel median |

## Key options

| Option | Default | Description |
|--------|---------|-------------|
| `-bands` | — | Band(s) to process, e.g. `1` or `1,2,3` |
| `-nodata VALUE` | from file | Input pixel value to treat as nodata |
| `-o PATH` | `./` | Output directory or explicit `.tif` filename |
| `-ot DTYPE` | auto | Output data type (`float32`, `uint16`, …) |
| `-p N` | cores − 1 | Number of parallel workers |
| `-chunks PX` | 1000 | Processing tile size in pixels |
| `-start YYYY-MM-DD` | — | Include only images on or after this date |
| `-end YYYY-MM-DD` | — | Include only images on or before this date |

---

## About

StackComposed was developed by the Group of Forest and Carbon Monitoring System (SMByC), operated by the Institute of Hydrology, Meteorology and Environmental Studies (IDEAM) — Colombia.

**Author and developer:** Xavier C. Llano
**Contact:** xavier.corredor.llano@gmail.com
**SMByC:** smbyc@ideam.gov.co

## License

StackComposed is free software, licensed under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html).
