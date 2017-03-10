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
import os


def calc_date(year, jday):
    return (datetime.datetime(year, 1, 1) + datetime.timedelta(jday - 1)).date()


def parse_filename(file_path):
    """
    Extract metadata from filename
    """

    #### LANDSAT PARSE FILENAME ####

    #### original structure of Landsat filename
    #
    # e.g. LE70080532002152EDC00SR_Enmask.tif
    try:
        filename = os.path.basename(file_path).split("_")[0].split(".")[0]
        filename = filename.upper()
        if filename[1] == "E":
            sensor = "ETM"
        if filename[1] in ["O", "C"]:
            sensor = "OLI"
        if filename[1] == "T":
            sensor = "TM"
        landsat_version = int(filename[2])
        path = int(filename[3:6])
        row = int(filename[6:9])
        year = int(filename[9:13])
        jday = int(filename[13:16])
        date = calc_date(year, jday)
        return landsat_version, sensor, path, row, date, jday
    except:
        pass

    #### SMBYC structure of Landsat filename
    #
    # e.g. Landsat_8_53_020601_7ETM_Reflec_SR_Enmask.tif
    try:
        filename = os.path.basename(file_path).split(".")[0]
        path = int(filename.split("_")[1])
        row = int(filename.split("_")[2])
        date = datetime.datetime.strptime(filename.split("_")[3], "%y%m%d").date()
        jday = date.timetuple().tm_yday
        landsat_version = int(filename.split("_")[4][0])
        sensor = filename.split("_")[4][1::]
        return landsat_version, sensor, path, row, date, jday
    except:
        pass

    raise Exception("Cannot parse filename for: {}".format(file_path))