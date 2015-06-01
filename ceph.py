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
from execo import logger, Remote, SshProcess, TaktukPut
from execo.log import style
from getpass import getuser
import sys
import yaml
from jinja2 import Template, Environment, PackageLoader



def start(config):
    """ Start the Ceph service
        Parameter:
            config: dict containing ceph configuration
    """
    # Check & cleanup the servers
    master_node = config["master"]

    cmd_mkcephfs = "mkcephfs -c /etc/ceph/ceph.conf --allhosts -v"
    # Launch command "mkcephfs" on master node
    mkcephfs = SshProcess(cmd_mkcephfs, master_node,
                          connection_params={'user': 'root'}).run()
    if not mkcephfs.ok:
        logger.info("mkcephfs failed on master node %s", master_node)
        return False

    cmd_startceph = "/etc/init.d/ceph -a start"
    # Start the Ceph master node
    startceph = SshProcess(cmd_startceph, master_node,
                           connection_params={'user': 'root'}).run()
    if not startceph.ok:
        logger.info("Ceph failed to start on master node %s", master_node)
        return False

    return True
# End of function start(config)


def stop(config):
    """ Stop the Ceph service 
        Parameter:
            config: dict containing ceph configuration
    """
    # Check & cleanup the servers
    master_node = config["master"]

    cmd_stopceph = "/etc/init.d/ceph -a stop"
    # Launch command "mkcephfs" on master node
    stopceph = SshProcess(cmd_stopceph, master_node,
                          connection_params={'user': 'root'}).run()
    if not stopceph.ok:
        logger.info("Failed to stop Ceph on master node %s", master_node)
        return False

    cmd_cleanlogs = "/etc/init.d/ceph cleanalllogs"
    # Start the Ceph master node
    cleanlogs = SshProcess(cmd_cleanlogs, master_node,
                           connection_params={'user': 'root'}).run()
    if not cleanlogs.ok:
        logger.info("Could not clean up Ceph logs on master node %s", master_node)
        return False

    # If the control came till this place, then everything is Ok, so return True
    return True
# End of function start(config)


def prepare_conf(config):
    """ Parse the config template file to fill in the Ceph configuration
        Parameter:
            config: dict containing Ceph configuration
        Returns: ceph.conf file
    """
    # Prepare the environment
    env = Environment(loader=PackageLoader('ceph', 'ceph'))
    # Read the file: ceph.conf.template
    template = env.get_template('ceph.conf.template')

    output = template.render(config)
    with open('ceph.conf', 'w') as f:
        f.write(output)
    return True
# End of function prepare_conf(config)


def init_servers(config):
    """ Initialise the Ceph master & data nodes 
        Parameter:
            config: dict containing ceph configuration
    """
    # Check & cleanup the servers
    logger.info('Checking the nodes in  the configuration file... ')
    if not check_servers(config):
       return False
    if not clean_servers(config):
       return False

    # Prepare template file and copy to all Ceph nodes
    conf_file = prepare_conf(config)
    if not send_config(config, ['ceph.conf']):
       return False

    # Prepare relevant directories on each Ceph data node and mount them
    data_nodes = config["dataNodes"]
    cmd_mnt = "mount -o remount,user_xattr " + config["dataDir"]
    counter = 0
    for node in data_nodes:

        # Create the ceph data directories
        cmd_mkdir = "mkdir -p " + config["dataDir"] + "/osd" + str(counter)
        mk_dir = SshProcess(cmd_mkdir, node, 
                            connection_params={'user': 'root'}).run()
        if not mk_dir.ok:
            logger.info("Failed to create Ceph directories on %s", node)
            return False  # Cannot proceed further so return here with fail

        # Mount the ceph data directories
        mnt = SshProcess(cmd_mnt, node, 
                         connection_params={'user': 'root'}).run()
        if not mnt.ok:
            logger.info("Failed to mount Ceph directories on %s", node)
            return False  # Cannot proceed further so return here with fail

        counter += 1

    logger.info("Ceph directories created & mounted on %s", data_nodes)

    # Configure ssh on Ceph nodes
    if not config_servers_ssh(config):
        return False

    # If control came till this point, then initialisation was Ok, so return True
    logger.info("Ceph initialisation OK")
    return True
# End of function init_servers(config)


def check_servers(config):
    """ Check if Ceph file system is installed 
        Parameter:
            config: dict containing ceph configuration
    """
    cmd_ls = "ls /etc/init.d/ceph"
    master_node = config["master"]
    data_nodes = config["dataNodes"]

    # Check if ceph FS is installed on master node
    path_exists = Remote(cmd_ls, [master_node] + data_nodes,
                         connection_params={'user': 'root'}).run()
    for p in path_exists.processes:
        if not p.ok:
            logger.info("Ceph FS not installed on node %s", p.host)
            return False

    # If control came till this point, then ceph installation is Ok, so return True
    logger.info("Ceph FS installation exists")
    return True
# End of function check_servers(config)


def clean_servers(config):
    """ Check if Ceph file system is installed 
        Parameter:
            config: dict containing ceph configuration
    """
    # Prepare 2 separate commands as they are different for master & datanodes
    cmd_rm_master = "rm -rf /etc/ceph " + config["dataDir"] + "/ceph.conf.* /var/run/ceph " + config["dataDir"] + "/osd* /tmp/mkfs.ceph* /tmp/mon0"
    master_node = config["master"]

    cmd_rm_data = "rm -rf /etc/ceph " + config["dataDir"] + "/ceph.conf.* /var/run/ceph " + config["dataDir"] + "/osd*"
    data_nodes = config["dataNodes"]

    # Clean up Ceph directories on master node
    rm_master = SshProcess(cmd_rm_master, master_node, 
                           connection_params={'user': 'root'}).run()
    if not rm_master.ok:
        logger.info("Failed to clean Metadata server %s", master_node)
        return False

    # Clean up Ceph directories on data nodes
    rm_data = Remote(cmd_rm_data, data_nodes, 
                     connection_params={'user': 'root'}).run()
    for p in rm_data.processes:
        if not p.ok:
            logger.info("Failed to clean data server %s", p.host)
            return False

    # If control came till this point, then cleanup was Ok, so return True
    logger.info("Existing Ceph directories cleaned up")
    return True
# End of function clean_servers(config)


def send_config(config, conf_file=['ceph.conf']):
    """ Send the config file to all Ceph nodes 
        Parameter:
            config: dict containing ceph configuration
            conf_file: config file to be sftp-ed - default file: ~/ceph.conf
    """
    cmd_rmdir = "rm -rf /etc/ceph /var/run/ceph"
    cmd_mkdir = "mkdir /etc/ceph && mkdir /var/run/ceph"
    master_node = config["master"]
    data_nodes = config["dataNodes"]

    # First remove any existing Ceph directories on master node
    rm_dir = Remote(cmd_rmdir, [master_node] + data_nodes, connection_params={'user': 'root'}).run()
    for p in rm_dir.processes:
        if not p.ok:
            logger.info("Failed to remove Ceph directories on server %s", p.host)
            return False
    logger.info("Removed all ceph directories")

    # Then create Ceph directories on master node
    mk_dir = Remote(cmd_mkdir, [master_node] + data_nodes, connection_params={'user': 'root'}).run()
    for p in mk_dir.processes:
        if not p.ok:
            logger.info("Failed to create Ceph directories on server %s", p.host)
            return False # Cannot proceed further, so return here with fail
    logger.info("Created ceph directories on Master node %s", master_node)

    # Next write conf_file to master node
    put_conf = TaktukPut([master_node] + data_nodes, ['ceph.conf'], "/etc/ceph", connection_params={'user': 'root'}).run()
    for p in put_conf.processes:
        if not p.ok:
            logger.info("Failed to write ceph.conf to server %s", p.host)
            return False # Cannot proceed further so return here with fail
    logger.info("Copied ceph configuration to all nodes")

    # If control came till this place, ceph config was correctly sent, so return True
    logger.info("Ceph config files sent to all nodes")
    return True
# End of function send_config(config, conf_file)


def deploy(config):
    """ Deploy the Ceph service 
        Parameter:
            config: dict containing ceph configuration
    """
    # Configure Ceph
    logger.info("Configuring the ceph file system...")
    if init_servers(config):
        logger.info("Starting the ceph file system...")
        start(config)
# End of function deploy(config)


def undeploy(config):
    """ End the deployment of the Ceph service 
        Parameter:
            config: dict containing ceph configuration
    """
    # Configure Ceph
    logger.info("Stopping ceph file system...")
    if stop(config):
        logger.info("Cleaning the servers...")
        clean_servers(config)
# End of function deploy(config)


def mount(action, config):
    """ Check if Ceph file system is installed 
        Parameter:
            action: "mount" or "umount"
            config: dict containing ceph configuration
    """
    master_node = config["master"]
    client_nodes = config["clients"]

    if action == "mount":
        cmd_mount = "mkdir -p /dfs && ceph-fuse -m  #{@master['addr']} /dfs"
    elif action == "umount":
        cmd_mount = "umount /dfs && rm -rf /dfs"

    # Check if ceph FS is installed on master node
    mount_fs = Remote(cmd_mount, client_nodes, connection_params={'user': 'root'}).run()
    for p in mount_fs.processes:
        if not p.ok:
            logger.info("Failed to mount Ceph directories on client %s", p.host)
            return False # Cannot proceed further, so return here with fail

    # If control came till this point ceph nodes were correctly mounted, so return True
    logger.info("Ceph nodes correctly %ed", action)
    return True
# End of function mount(action, config)


def config_servers_ssh(config):
    """ Push ssh keys to all Ceph nodes 
        Parameter:
            config: dict containing ceph configuration
    """
    master_node = config["master"]
    data_nodes = config["dataNodes"]

    # Create ssh commands
    cmd_auth_keys = "cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys ; ssh-keygen -R {{{host}}}; ssh-keyscan -H {{{host}}} >> .ssh/known_hosts"

    # Push ssh keys to nodes
    push_auth_keys = Remote(cmd_auth_keys, [master_node] + data_nodes, connection_params={'user': 'root'}).run()
    if not push_auth_keys.ok:
        logger.info("Failed to push ssh keys to authorized_keys table in master %s", node)
        return False # Cannot proceed further, so return here with fail

    # If control came till this point ssh config is OK, so return True
    logger.info("ssh configured on all ceph nodes")
    return True
# End of function config_servers_ssh(config)
