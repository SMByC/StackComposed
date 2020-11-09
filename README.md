# StackComposed
 
The StackComposed compute the stack composed of a specific statistic of band values for several time series of georeferenced data (such as Landsat images), even if these are in different scenes or tiles. The result is a output of statistic compute for all valid pixels values across the time axis (z-axis), in the wrapper extent for all input data in parallels process.

## Documentation

Home page documentation: [https://github.com/SMByC/StackComposed](https://github.com/SMByC/StackComposed)

## Source code

The latest sources can be obtained from official repository:
[https://smbyc.github.io/StackComposed](https://smbyc.github.io/StackComposed)

## Issue Tracker

Issues, ideas and enhancements: [https://github.com/SMByC/StackComposed/issues](https://github.com/SMByC/StackComposed/issues)

## Installation

The StackComposed use the following apps/libraries:

* Python3
* Gdal
* Numpy
* [Dask](http://dask.pydata.org)

### Using Pip

You can install from PyPi repository:

```bash
pip3 install stack-composed
```

### From source code

To install StackComposed from source, clone the repository from Bitbucket

```bash
hg clone https://bitbucket.org/smbyc/stackcomposed
cd stackcomposed
python3 setup.py install
# or
pip3 install -e .
```

## About us

StackComposed was developing, designed and implemented by the Group of Forest and Carbon Monitoring System (SMByC), operated by the Institute of Hydrology, Meteorology and Environmental Studies (IDEAM) - Colombia.

Author and developer: *Xavier Corredor Ll.*  
Theoretical support, tester and product verification: SMByC-PDI group

### Contact

Xavier Corredor Ll.: *xcorredorl (a) ideam.gov.co*  
SMByC: *smbyc (a) ideam.gov.co*

## License

StackComposed is a free/libre software and is licensed under the GNU General Public License.