__version__ = '25.3'  # year.month.revision

header = """\
====================================================================

  StackComposed v{ver}

  Compute statistics over a stack of georeferenced raster images.
  Processes any GeoTIFF/ENVI input across different tiles or
  extents, writing results to a wrapper extent.

  Run with '-h' for full usage, or read the project README:
  https://github.com/SMByC/StackComposed#readme

====================================================================\
""".format(ver=__version__)

epilog = """\
Statistics reference
--------------------
  median            Median value across the time axis
  mean              Arithmetic mean
  gmean             Geometric mean (positive values only)
  sum               Sum of valid pixel values
  max               Maximum value
  min               Minimum value
  std               Standard deviation
  valid_pixels      Count of valid (non-nodata) observations
  last_pixel        Value of the most recent valid pixel
  jday_last_pixel   Julian day of the most recent valid pixel
  jday_median       Julian day of the temporal median
  linear_trend      Linear regression slope (×10⁶, int32 output)
  extract_NN        Isolate pixels equal to integer value NN
  percentile_NN     NN-th percentile (e.g. percentile_25)
  trim_mean_LL_UL   Mean after trimming outside the LL–UL percentile
                    range (e.g. trim_mean_10_90)

Preprocessing (-preproc)
------------------------
  >3                Keep only pixels greater than 3
  >=1 and <=5       Keep pixels within the range [1, 5]
  percentile_10_90  Keep only values in the 10th–90th percentile
  2.5_std_devs      Keep values within 2.5 standard deviations of
                    the per-pixel mean
  1.5_IQR           Keep values within 1.5 × IQR of the median

For more information visit:
  https://github.com/SMByC/StackComposed#readme

StackComposed v{ver}  —  SMByC-IDEAM\
""".format(ver=__version__)
