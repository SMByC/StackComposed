# -*- coding: utf-8 -*-

import os
import re
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'stack_composed', '__init__.py'), encoding='utf-8') as fp:
    version = re.search("__version__ = '([^']+)'", fp.read()).group(1)
try:
    import pypandoc
    # convert md to rst for PyPi
    long_description = pypandoc.convert(os.path.join(here, 'README.md'), 'rst')
except(IOError, ImportError):
    with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()

setup(
    name='stack-composed',
    version=version,
    description='Compute and generate the composed of a raster images stack',
    long_description=long_description,
    author='Xavier Corredor Llano, SMBYC',
    author_email='xcorredorl@ideam.gov.co',
    url='https://smbyc.bitbucket.io/stackcomposed',
    license='GPLv3',
    packages=find_packages(),
    install_requires=['gdal',
                      'numpy',
                      'dask[array]',
                      'dask[bag]'],
    scripts=['bin/stack-composed'],
    platforms=['Any'],
    keywords='stack composed statistics landsat raster gis',
    classifiers=[
        "Topic :: Scientific/Engineering :: GIS",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python",
        "Environment :: Console",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"],
)
