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

from stack_composed.parse import parse_filename


class Image:

    def __init__(self, file_path):
        self.file_path = file_path

    def get_extent(self):
        # TODO
        self.extent = None

    def get_metadata(self):
        # TODO
        print(parse_filename(self.file_path))
