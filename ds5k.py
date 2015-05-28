#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    ds5k: A script for deploying easily a Distributed File System (DFS) on Grid'5000
#     Created by Anirvan B., Laurent P., Matthieu I. (INRIA, 2015-2016)
#
#    Developped by the Laplace ADT, 2015-2016
#    https://www.grid5000.fr/mediawiki/index.php/DFS5K_with_Execo
#
from argparse import ArgumentParser, RawTextHelpFormatter
from time import time
from datetime import timedelta
from execo import *
from execo_g5k import *
from getpass import getuser
from execo.log import style
from execo.host import *
from getpass import getuser
import sys
from string import Template

prog = 'ds5k'

def reserve_storage(storage_site='rennes', data_size=50, walltime='24:00:00'):
    """ Reserve storage on the storage_site using storage5k 
        Parameters:
            storage_site: site where chunks will be reserved - default - rennes
            data_size: size of space to be reserved (in GB) - default - 50GB
            walltime: duration of reservation (in hours:mins:seconds) - default - 24h
       Returns: Dict storage
    """
    storage ={}  # Empty dict

    # Get the size of a 'chunk' - this is fixed (generally 10GB) over all sites.
    get_chunk_size = SshProcess("storage5k -a chunk_size | cut -f 4 -d ' '", storage_site).run()
    chunk_size = int(get_chunk_size.stdout[1:])
    chunks_count = int(data_size / chunk_size)
    get_storage = SshProcess("storage5k -a add -l chunks=" + str(chunks_count) + ',walltime=' + str(walltime), storage_site).run()
    user = getuser()
    for s in get_storage.stdout.split('\n'):
        if 'OAR_JOB_ID' in s:
            storage_job_id = int(s.split('=')[1])
            break
    logger.info('Storage available on %s: /data/%s_%s', storage_site, user, storage_job_id)
    # Fill up the "storage" dict and return
    storage['storage_site'] = storage_site
    storage['data_size'] = data_size
    storage['walltime'] = walltime
    storage['chunk_size'] = chunk_size
    storage['chunks_count'] = chunks_count
    storage['storage_job_id'] = storage_job_id
    storage['path'] = "/data/" + user + "_" + str(storage_job_id)

    return storage
# End of function reserve_storage(storage_site, data_size, walltime)


def reserve_compute_nodes(compute_site='rennes', nodes_count=3, walltime='1:00:00'):
    """ Reserve compute nodes on the site for computing 
        Parameters:
            compute_site: site where compute nodes will be reserved - default - rennes
            nodes_number: no. of nodes to be reserved (in GB) - default - 1 node
            walltime: duration of reservation (in hours:mins:seconds) - default - 1h
       Returns: Dict hosts - list of nodes reserved
    """
    # Get the size of a 'chunk' - this is fixed (generally 10GB) over all sites.
    logger.info('Reserving %s node(s) on site %s', nodes_count, compute_site)
    jobs = oarsub([(OarSubmission(resources="nodes=" + str(nodes_count),
                                  job_type="deploy",
                                  walltime=walltime,
                                  name="ds5k"), compute_site)])

    hosts = get_oar_job_nodes(jobs[0][0], compute_site)
    logger.info('Reserved %s', hosts)
    return hosts
# End of function reserve_compute_nodes(compute_site, nodes_count, walltime)


def deploy_compute_nodes(hosts, env_name='wheezy-x64-prod'):
    """ Deploy compute nodes that were reserved 
        Parameters:
            hosts: dict containing details of nodes reserved
            env: deployment environment - default - wheezy-x64-prod (contains all DFS)
    """
    # Deploy the environment on the compute nodes
    logger.info('Deploying %s environment on reserved nodes %s', env_name, get_hosts_list(hosts))
    deployed, undeployed = deploy(Deployment(hosts, env_name=env_name))
    return list(deployed)
# End of function reserve_compute_nodes(compute_site, nodes_count, walltime)




