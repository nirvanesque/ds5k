#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    ds5k: A script for deploying easily a Distributed File System (DFS) on Grid'5000
#     Created by Anirvan B., Laurent P., Matthieu I. (INRIA, 2015-2016)
#
#    Developped by the Laplace ADT, 2015-2016
#    https://www.grid5000.fr/mediawiki/index.php/DFS5K_with_Execo
#
import ds5k
import ceph

# Simple workflow for deploying a ceph DFS
# Assumes simple static parameters hard-coded in script
# Experiment based on Rennes site
# 1. Reserve storage.
storage = ds5k.reserve_storage(storage_site='rennes', data_size=50, walltime='24:00:00')

# 2. Reserve 4 compute nodes.
hosts = ds5k.reserve_compute_nodes(compute_site='rennes', nodes_count=4, walltime='1:00:00')

# 3. Deploy the reserved nodes.
deployed = ds5k.deploy_compute_nodes(hosts)

# 4. Read ds5k config file. 
#    (Ceph conf file is prepared later when ceph.deploy() is called)
config = ds5k.parse_conf(hosts, "ds5k.conf")

# 5. Initialise ndoes for ceph
ceph.deploy(config)

# 6. Cleaning up reservations (storage & nodes)
# logger.info('Destroying jobs')
# As of now delete only storage. 
# delete_jobs(storage)

