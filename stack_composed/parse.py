#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2016-2017 Xavier Corredor Llano, SMBYC
#  Email: xcorredorl at ideam.gov.co
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
import datetime


def calc_date(year, jday):
    return (datetime.datetime(year, 1, 1) + datetime.timedelta(jday - 1)).date()


def parse_filename(file_path):
    """
    Extract metadata from filename
    """

    #### original structure of Landsat filename

    landsat_id = file_path.split("_")[0].split(".")[0]
    print(file_path)
    print(landsat_id)
    landsat_id = landsat_id.upper()
    if landsat_id[1] == "E":
        sensor = "ETM"
    if landsat_id[1] in ["O", "C"]:
        sensor = "OLI"
    if landsat_id[1] == "T":
        sensor = "TM"
    landsat_version = int(landsat_id[2])
    path = int(landsat_id[3:6])
    row = int(landsat_id[6:9])
    year = int(landsat_id[9:13])
    jday = int(landsat_id[13:16])
    date = calc_date(year, jday)
    return sensor, landsat_version, path, row, date


