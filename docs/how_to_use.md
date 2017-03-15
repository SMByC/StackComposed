# How to use

This is a mini guide step by step for use the StackComposed

## Recommendation for data input

There are some recommendation for the data input for process, all input images need:

- To be in the same projection
- Have the same pixel size
- Have pixel registration

For the moment, the image formats support are: `tif` and `img`

## Usage

`StackComposed` takes some command-line options:

```bash
stack-composed -stat STAT -bands BANDS [-p P] [-chunks CHUNKS] [-o OUTPUT] [-ot dtype] inputs
```

- `-stat` STAT (required)
    - statistic for compute the composed along the time axis ignoring any nans, this is, compute the statistic along the time series by pixel (see [about](about.md))
    - statistics options:
        - `median`: compute the median
        - `mean`: compute the arithmetic mean
        - `gmean`: compute the geometric mean, that is the n-th root of (x1 * x2 * ... * xn)
        - `max`: compute the maximum value
        - `min`: compute the minimum value
        - `std`: compute the standard deviation
        - `valid_pixels`: count the valid pixels
        - `last_pixel`: the last valid pixel base on the date of the raster image, required extra metadata [\[2\]](#2)
        - `jday_last_pixel`: the julian day of the last valid pixel base on the date of the raster image, required extra metadata [\[2\]](#2)
        - `percentile_nn`: compute the percentile nn, for example, for percentile 25 put "percentile_25" (must be in the range 0-100)
        - `trim_mean_LL_UL`: compute the truncated mean, first clean the time pixels series below to percentile LL (lower limit) and above the percentile UL (upper limit) then compute the mean
    - example: -stat median

- `-bands` BANDS (required)
    - band or bands to process
    - input: integer or integers comma separated
    - example: -bands 1,2,4

- `-p` P (optional)
    - number of process
    - input: integer
    - by default: total cores - 1
    - example: -p 10

- `-chunks` CHUNKS (optional)
    - chunks size for parallel process [\[1\]](#1)
    - input: integer
    - by default: 1000
    - example: -chunks 800

- `-o` OUTPUT (optional)
    - output directory and/or filename for save results
    - input: string, absolute or relative path or filename
    - by default: save in the same directory of run with a standard name
    - example: -o /dir/to/file.tif

- `-ot` DTYPE (optional)
    - output data type for results
    - options: byte, uint16, uint32, int16, int32, float32, float64
    - example: -ot float64

- `-start` DATE (optional)
    - filter the images with the start date DATE, can be used alone or in combination with -end argument, required extra metadata [\[2\]](#2)
    - format: YYYY-MM-DD
    - example: -start 2016-06-01

- `-end` DATE (optional)
    - filter the images with the end date DATE, can be used alone or in combination with -start argument, required extra metadata [\[2\]](#2)
    - format: YYYY-MM-DD
    - example: -end 2016-12-31

- `inputs` (required)
    - directories or images files to process
    - input: filenames and/or absolute or relative directories
    - example: /dir1 /dir2 *.tif

### \[1\] Chunks sizes<a name="1"></a>

Choosing good values for chunks can strongly impact performance. StackComposed only required a ram memory enough only for the sizes and the number of chunks that are currently being processed in parallel, therefore the chunks sizes going together with the number of process. Here are some general guidelines. The strongest guide is memory:

- The size of your blocks should fit in memory.

- Actually, several blocks should fit in memory at once, assuming you want multi-core

- The size of the blocks should be large enough to hide scheduling overhead, which is a couple of milliseconds per task

### \[2\] Extra metadata<a name="2"></a>

Some statistics or arguments required extra information for each image to process. The StackComposed acquires this extra metadata using parsing of the filename. Currently support two format:

* **Official Landsat filenames:**
    * Example: LE70080532002152EDC00...tif

* **SMByC format:**
    * Example: Landsat_8_53_020601_7ETM...tif

For them extract: landsat version, sensor, path, row, date and julian day.