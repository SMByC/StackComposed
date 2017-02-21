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

- `-stat` STAT
    - statistic for compute the composed (required)
    - options: median, mean, max, min, std, valid_pixels
    - example: -stat mean

- `-bands` BANDS
    - band or bands to process (required)
    - input: integer or integers comma separated
    - example: -bands 1,2,4

- `-p` P
    - number of process (optional)
    - input: integer
    - by default: total cores - 1
    - example: -p 10

- `-chunks` CHUNKS
    - chunks size for parallel process (optional)
    - input: integer
    - by default: 1000
    - example: -chunks 800

- `-o` OUTPUT
    - output directory and/or filename for save results (optional)
    - input: string, absolute or relative path or filename
    - by default: save in the same directory of run with a standard name
    - example: -o /dir/to/file.tif

- `-ot` DTYPE
    - output data type for results (optional)
    - options: byte, uint16, uint32, int16, int32, float32, float64
    - example: -ot float64

- `inputs`
    - directories or images files to process (required)
    - input: strings, absolute or relative directories or/and files
    - example: /dir1 /dir2 *.tif

### Chunks sizes

Choosing good values for chunks can strongly impact performance. StackComposed only required a ram memory enough only for the sizes and the number of chunks that are currently being processed in parallel, therefore the chunks sizes going together with the number of process. Here are some general guidelines. The strongest guide is memory:

- The size of your blocks should fit in memory.

- Actually, several blocks should fit in memory at once, assuming you want multi-core

- The size of the blocks should be large enough to hide scheduling overhead, which is a couple of milliseconds per task

