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

# disable the firewall:
# systemctl status firewalld
# systemctl stop firewalld

# setting up PYTHONPATH
# .bashrc
# export PYTHONPATH=$PYTHONPATH:/opt/smbyc/stack-composed


import os
from dask.distributed import Client, SSHCluster

# add project dir to pythonpath
project_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if project_dir not in os.sys.path:
    os.sys.path.append(project_dir)

# get the password from environment variable
password = os.environ.get('PASSWORD')

from stack_composed import stack_composed_main

# Create a list of addresses for your servers
addresses = ['192.168.106.12', '192.168.106.13']

# Specify SSH keys and other SSH settings
connect_options = {
    'username': 'smbyc',
    'password': password,
    'known_hosts': None
}

# Create an SSHCluster instance
cluster = SSHCluster(addresses, connect_options=connect_options, worker_options={"nthreads": 32, "n_workers": 2},)

# Connect to the cluster
client = Client(cluster)

# Perform computations using the Dask client
stack_composed_main.cli()

# Close the client and cluster when done
client.close()
cluster.close()


