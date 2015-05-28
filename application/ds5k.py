#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    ds5k: A script for deploying easily a Distributed File System (DFS) on Grid'5000
#     Created by Anirvan BASU, Laurent POUILLOUX, Matthieu IMBERT (INRIA, 2015-2016)
#
#    Developped by the Laplace ADT, 2015-2016
#    https://www.grid5000.fr/mediawiki/index.php/DFS5K_with_Execo
#
from argparse import ArgumentParser, RawTextHelpFormatter
from time import time
from datetime import timedelta
from execo import logger, Remote
from execo.log import style
from getpass import getuser
import yaml
import sys
from string import Template

prog = 'ds5k'
description = 'This tool helps you to create a DFS of your choice on the ' + \
    style.log_header("Grid'5000") + ' platform. 3 possible DFS can be deployed: \n - ' + \
    style.host('date') + ' = give you the number of nodes available at a given date, \n - ' + \
    style.host('free') + ' = find the next free slot for a combination of resources, \n - ' + \
    style.host('max') + '  = find the time slot where the maximum number of nodes are available.\n\n' + \
    """If no arguments is given, compile the planning of the whole platform and generate an
    oargridsub command line with all available resources for 1 hour.
    Based on execo 2.2, """ + style.emph('http://execo.gforge.inria.fr/doc/') + \
    'oar 2.5, ' + style.emph('http://oar.imag.fr') + """
    and the Grid'5000 Job API, """ + style.emph('https://api.grid5000.fr') + '.'

epilog = style.host('Examples:') + \
    '\nNumber of available nodes on stremi cluster from date to date + walltime \n' + \
    style.command('  %(prog)s -m date -s "' + \
    format_oar_date(int(time() + timedelta_to_seconds(timedelta( minutes = 1)))) + \
    '" -r stremi\n') + \
    'First free slots for a resource combination with deploy job type and a KaVLAN\n' + \
    style.command('  %(prog)s -m free -w 2:00:00 -r grid5000:100,taurus:4 -o "-t deploy" -k\n') + \
    'Maximum number of nodes available for the resources, avoiding charter periods\n' +\
    style.command('  %(prog)s -m max -w 10:00:00 -r nancy,paradent,edel -c \n') + \
    'Issues/features requests can be reported to ' + style.emph('https://github.com/nirvanesque/ds5k')




def reserve_storage(storage_site='rennes', data_size=50, walltime='24:00:00'):
    """ Reserve storage on the storage_site using storage5k 
        Parameters:
            storage_site: site where chunks will be reserved - default - rennes
            data_size: size of space to be reserved (in GB) - default - 50GB
            walltime: duration of reservation (in hours:mins:seconds) - default - 24h
    """
    # Get the size of a 'chunk' - this is fixed (generally 10GB) over all sites.
    get_chunk_size = SshProcess("storage5k -a chunk_size | cut -f 4 -d ' '", storage_site).run()
    chunk_size = int(get_chunk_size.stdout[1:])
    chunks_number = int(data_size / chunk_size)
    get_storage = SshProcess("storage5k -a add -l chunks=" + str(chunks_number) + ',walltime=' + str(walltime), storage_site).run()
    for s in get_storage.stdout.split('\n'):
        if 'OAR_JOB_ID' in s:
            storage_job_id = int(s.split('=')[1])
            break
    logger.info('Storage available on %s: /data/%s_%s', storage_site, user, storage_job_id)
# Concat here to form /data/userid_storage_job_id and return as "storage"
    return storage
# End of function reserve_storage(storage_site, data_size, walltime)


def reserve_compute_nodes(compute_site='rennes', nodes_number=1, walltime='1:00:00'):
    """ Reserve compute nodes on the site for computing 
        Parameters:
            compute_site: site where compute nodes will be reserved - default - rennes
            nodes_number: no. of nodes to be reserved (in GB) - default - 1 node
            walltime: duration of reservation (in hours:mins:seconds) - default - 1h
    """
    # Get the size of a 'chunk' - this is fixed (generally 10GB) over all sites.
    logger.info('Reserving a node on %s', compute_site)
    jobs = oarsub([(OarSubmission(resources="nodes=1",
                                  job_type="deploy",
                                  walltime,
                                  name="G5kDFS"), compute_site)])

    hosts = get_oar_job_nodes(jobs[0][0], distant_site)
    logger.info('Reserved %s', hosts[0].address)
    return hosts
# End of function reserve_compute_nodes(compute_site, nodes_number, walltime)


