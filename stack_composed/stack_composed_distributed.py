#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2016-2025 Xavier C. Llano, SMBYC
#  Email: xavier.corredor.llano@gmail.com
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#

import argparse


def cli(argv=None):
    parser = argparse.ArgumentParser(
        prog="stack-composed-distributed",
        description="Distributed execution is not available in this release.",
    )
    parser.parse_known_args(argv)
    parser.error(
        "distributed execution is not available because the current processing "
        "engine uses local worker processes; use stack-composed with -p for local parallelism"
    )


if __name__ == "__main__":
    cli()
