# Copyright 2017-2018 Sandvine
# Copyright 2018 Telefonica
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
OSM shell/cli
"""

import click
from osmclient import client
from osmclient.common.exceptions import ClientException
from prettytable import PrettyTable
import yaml
import json
import time

def check_client_version(obj, what, version='sol005'):
    '''
    Checks the version of the client object and raises error if it not the expected.

    :param obj: the client object
    :what: the function or command under evaluation (used when an error is raised)
    :return: -
    :raises ClientError: if the specified version does not match the client version
    '''
    fullclassname = obj.__module__ + "." + obj.__class__.__name__
    message = 'The following commands or options are only supported with the option "--sol005": {}'.format(what)
    if version == 'v1':
        message = 'The following commands or options are not supported when using option "--sol005": {}'.format(what)
    if fullclassname != 'osmclient.{}.client.Client'.format(version):
        raise ClientException(message)
    return

@click.group()
@click.option('--hostname',
              default=None,
              envvar='OSM_HOSTNAME',
              help='hostname of server.  ' +
                   'Also can set OSM_HOSTNAME in environment')
@click.option('--so-port',
              default=None,
              envvar='OSM_SO_PORT',
              help='hostname of server.  ' +
                   'Also can set OSM_SO_PORT in environment')
@click.option('--so-project',
              default=None,
              envvar='OSM_SO_PROJECT',
              help='Project Name in SO.  ' +
                   'Also can set OSM_SO_PROJECT in environment')
@click.option('--ro-hostname',
              default=None,
              envvar='OSM_RO_HOSTNAME',
              help='hostname of RO server.  ' +
              'Also can set OSM_RO_HOSTNAME in environment')
@click.option('--ro-port',
              default=9090,
              envvar='OSM_RO_PORT',
              help='hostname of RO server.  ' +
                   'Also can set OSM_RO_PORT in environment')
@click.option('--sol005/--no-sol005',
              default=True,
              envvar='OSM_SOL005',
              help='Use ETSI NFV SOL005 API (default) or the previous SO API')
@click.pass_context
def cli(ctx, hostname, so_port, so_project, ro_hostname, ro_port, sol005):
    if hostname is None:
        print((
            "either hostname option or OSM_HOSTNAME " +
            "environment variable needs to be specified"))
        exit(1)
    kwargs={}
    if so_port is not None:
        kwargs['so_port']=so_port
    if so_project is not None:
        kwargs['so_project']=so_project
    if ro_hostname is not None:
        kwargs['ro_host']=ro_hostname
    if ro_port is not None:
        kwargs['ro_port']=ro_port
    
    ctx.obj = client.Client(host=hostname, sol005=sol005, **kwargs)


####################
# LIST operations
####################

@cli.command(name='ns-list')
@click.option('--filter', default=None,
              help='restricts the list to the NS instances matching the filter')
@click.pass_context
def ns_list(ctx, filter):
    '''list all NS instances'''
    if filter:
        check_client_version(ctx.obj, '--filter')
        resp = ctx.obj.ns.list(filter)
    else:
        resp = ctx.obj.ns.list()
    table = PrettyTable(
        ['ns instance name',
         'id',
         'operational status',
         'config status',
         'detailed status'])
    for ns in resp:
        fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
        if fullclassname == 'osmclient.sol005.client.Client':
            nsr = ns
            nsr_name = nsr['name']
            nsr_id = nsr['_id']
        else:
            nsopdata = ctx.obj.ns.get_opdata(ns['id'])
            nsr = nsopdata['nsr:nsr']
            nsr_name = nsr['name-ref']
            nsr_id = nsr['ns-instance-config-ref']
        opstatus = nsr['operational-status'] if 'operational-status' in nsr else 'Not found'
        configstatus = nsr['config-status'] if 'config-status' in nsr else 'Not found'
        detailed_status = nsr['detailed-status'] if 'detailed-status' in nsr else 'Not found'
        if configstatus == "config_not_needed":
            configstatus = "configured (no charms)"
        table.add_row(
            [nsr_name,
             nsr_id,
             opstatus,
             configstatus,
             detailed_status])
    table.align = 'l'
    print(table)


def nsd_list(ctx, filter):
    if filter:
        check_client_version(ctx.obj, '--filter')
        resp = ctx.obj.nsd.list(filter)
    else:
        resp = ctx.obj.nsd.list()
    #print yaml.safe_dump(resp)
    table = PrettyTable(['nsd name', 'id'])
    fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
    if fullclassname == 'osmclient.sol005.client.Client':
        for ns in resp:
            name = ns['name'] if 'name' in ns else '-'
            table.add_row([name, ns['_id']])
    else:
        for ns in resp:
            table.add_row([ns['name'], ns['id']])
    table.align = 'l'
    print(table)


@cli.command(name='nsd-list')
@click.option('--filter', default=None,
              help='restricts the list to the NSD/NSpkg matching the filter')
@click.pass_context
def nsd_list1(ctx, filter):
    '''list all NSD/NSpkg in the system'''
    nsd_list(ctx,filter)


@cli.command(name='nspkg-list')
@click.option('--filter', default=None,
              help='restricts the list to the NSD/NSpkg matching the filter')
@click.pass_context
def nsd_list2(ctx, filter):
    '''list all NSD/NSpkg in the system'''
    nsd_list(ctx,filter)


def vnfd_list(ctx, filter):
    if filter:
        check_client_version(ctx.obj, '--filter')
        resp = ctx.obj.vnfd.list(filter)
    else:
        resp = ctx.obj.vnfd.list()
    #print yaml.safe_dump(resp)
    table = PrettyTable(['vnfd name', 'id'])
    fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
    if fullclassname == 'osmclient.sol005.client.Client':
        for vnfd in resp:
            name = vnfd['name'] if 'name' in vnfd else '-'
            table.add_row([name, vnfd['_id']])
    else:
        for vnfd in resp:
            table.add_row([vnfd['name'], vnfd['id']])
    table.align = 'l'
    print(table)


@cli.command(name='vnfd-list')
@click.option('--filter', default=None,
              help='restricts the list to the VNFD/VNFpkg matching the filter')
@click.pass_context
def vnfd_list1(ctx, filter):
    '''list all VNFD/VNFpkg in the system'''
    vnfd_list(ctx,filter)


@cli.command(name='vnfpkg-list')
@click.option('--filter', default=None,
              help='restricts the list to the VNFD/VNFpkg matching the filter')
@click.pass_context
def vnfd_list2(ctx, filter):
    '''list all VNFD/VNFpkg in the system'''
    vnfd_list(ctx,filter)


@cli.command(name='vnf-list')
@click.option('--ns', default=None, help='NS instance id or name to restrict the VNF list')
@click.pass_context
def vnf_list(ctx, ns):
    ''' list all VNF instances'''
    try:
        if ns:
            check_client_version(ctx.obj, '--ns')
            resp = ctx.obj.vnf.list(ns)
        else:
            resp = ctx.obj.vnf.list()
    except ClientException as inst:
        print((inst.message))
        exit(1)
    fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
    if fullclassname == 'osmclient.sol005.client.Client':
        table = PrettyTable(
            ['vnf id',
             'name',
             'ns id',
             'vnf member index',
             'vnfd name',
             'vim account id',
             'ip address'])
        for vnfr in resp:
            name = vnfr['name'] if 'name' in vnfr else '-'
            table.add_row(
                [vnfr['_id'],
                 name,
                 vnfr['nsr-id-ref'],
                 vnfr['member-vnf-index-ref'],
                 vnfr['vnfd-ref'],
                 vnfr['vim-account-id'],
                 vnfr['ip-address']])
    else:
        table = PrettyTable(
            ['vnf name',
             'id',
             'operational status',
             'config status'])
        for vnfr in resp:
            if 'mgmt-interface' not in vnfr:
                vnfr['mgmt-interface'] = {}
                vnfr['mgmt-interface']['ip-address'] = None
            table.add_row(
                [vnfr['name'],
                 vnfr['id'],
                 vnfr['operational-status'],
                 vnfr['config-status']])
    table.align = 'l'
    print(table)

@cli.command(name='ns-op-list')
@click.argument('name')
@click.pass_context
def ns_op_list(ctx, name):
    '''shows the history of operations over a NS instance

    NAME: name or ID of the NS instance
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name)
        resp = ctx.obj.ns.list_op(name)
    except ClientException as inst:
        print((inst.message))
        exit(1)

    table = PrettyTable(['id', 'operation', 'status'])
    for op in resp:
         table.add_row([op['id'], op['lcmOperationType'],
                        op['operationState']])
    table.align = 'l'
    print(table)

####################
# SHOW operations
####################

def nsd_show(ctx, name, literal):
    try:
        resp = ctx.obj.nsd.get(name)
        #resp = ctx.obj.nsd.get_individual(name)
    except ClientException as inst:
        print((inst.message))
        exit(1)

    if literal:
        print(yaml.safe_dump(resp))
        return

    table = PrettyTable(['field', 'value'])
    for k, v in list(resp.items()):
        table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='nsd-show', short_help='shows the content of a NSD')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.argument('name')
@click.pass_context
def nsd_show1(ctx, name, literal):
    '''shows the content of a NSD

    NAME: name or ID of the NSD/NSpkg
    '''
    nsd_show(ctx, name, literal)


@cli.command(name='nspkg-show', short_help='shows the content of a NSD')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.argument('name')
@click.pass_context
def nsd_show2(ctx, name, literal):
    '''shows the content of a NSD

    NAME: name or ID of the NSD/NSpkg
    '''
    nsd_show(ctx, name, literal)


def vnfd_show(ctx, name, literal):
    try:
        resp = ctx.obj.vnfd.get(name)
        #resp = ctx.obj.vnfd.get_individual(name)
    except ClientException as inst:
        print((inst.message))
        exit(1)

    if literal:
        print(yaml.safe_dump(resp))
        return

    table = PrettyTable(['field', 'value'])
    for k, v in list(resp.items()):
        table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='vnfd-show', short_help='shows the content of a VNFD')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.argument('name')
@click.pass_context
def vnfd_show1(ctx, name, literal):
    '''shows the content of a VNFD

    NAME: name or ID of the VNFD/VNFpkg
    '''
    vnfd_show(ctx, name, literal)


@cli.command(name='vnfpkg-show', short_help='shows the content of a VNFD')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.argument('name')
@click.pass_context
def vnfd_show2(ctx, name, literal):
    '''shows the content of a VNFD

    NAME: name or ID of the VNFD/VNFpkg
    '''
    vnfd_show(ctx, name, literal)


@cli.command(name='ns-show', short_help='shows the info of a NS instance')
@click.argument('name')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.option('--filter', default=None)
@click.pass_context
def ns_show(ctx, name, literal, filter):
    '''shows the info of a NS instance

    NAME: name or ID of the NS instance
    '''
    try:
        ns = ctx.obj.ns.get(name)
    except ClientException as inst:
        print((inst.message))
        exit(1)

    if literal:
        print(yaml.safe_dump(ns))
        return

    table = PrettyTable(['field', 'value'])

    for k, v in list(ns.items()):
        if filter is None or filter in k:
            table.add_row([k, json.dumps(v, indent=2)])

    fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
    if fullclassname != 'osmclient.sol005.client.Client':
        nsopdata = ctx.obj.ns.get_opdata(ns['id'])
        nsr_optdata = nsopdata['nsr:nsr']
        for k, v in list(nsr_optdata.items()):
            if filter is None or filter in k:
                table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='vnf-show', short_help='shows the info of a VNF instance')
@click.argument('name')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.option('--filter', default=None)
@click.pass_context
def vnf_show(ctx, name, literal, filter):
    '''shows the info of a VNF instance

    NAME: name or ID of the VNF instance
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name)
        resp = ctx.obj.vnf.get(name)
    except ClientException as inst:
        print((inst.message))
        exit(1)

    if literal:
        print(yaml.safe_dump(resp))
        return

    table = PrettyTable(['field', 'value'])
    for k, v in list(resp.items()):
        if filter is None or filter in k:
            table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='vnf-monitoring-show')
@click.argument('vnf_name')
@click.pass_context
def vnf_monitoring_show(ctx, vnf_name):
    try:
        check_client_version(ctx.obj, ctx.command.name, 'v1')
        resp = ctx.obj.vnf.get_monitoring(vnf_name)
    except ClientException as inst:
        print((inst.message))
        exit(1)

    table = PrettyTable(['vnf name', 'monitoring name', 'value', 'units'])
    if resp is not None:
        for monitor in resp:
            table.add_row(
                [vnf_name,
                 monitor['name'],
                    monitor['value-integer'],
                    monitor['units']])
    table.align = 'l'
    print(table)


@cli.command(name='ns-monitoring-show')
@click.argument('ns_name')
@click.pass_context
def ns_monitoring_show(ctx, ns_name):
    try:
        check_client_version(ctx.obj, ctx.command.name, 'v1')
        resp = ctx.obj.ns.get_monitoring(ns_name)
    except ClientException as inst:
        print((inst.message))
        exit(1)

    table = PrettyTable(['vnf name', 'monitoring name', 'value', 'units'])
    for key, val in list(resp.items()):
        for monitor in val:
            table.add_row(
                [key,
                 monitor['name'],
                    monitor['value-integer'],
                    monitor['units']])
    table.align = 'l'
    print(table)

@cli.command(name='ns-op-show', short_help='shows the info of an operation')
@click.argument('id')
@click.option('--filter', default=None)
@click.pass_context
def ns_op_show(ctx, id, filter):
    '''shows the detailed info of an operation

    ID: operation identifier
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name)
        op_info = ctx.obj.ns.get_op(id)
    except ClientException as inst:
        print((inst.message))
        exit(1)

    table = PrettyTable(['field', 'value'])
    for k, v in list(op_info.items()):
        if filter is None or filter in k:
            table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


####################
# CREATE operations
####################

def nsd_create(ctx, filename, overwrite):
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.nsd.create(filename, overwrite)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='nsd-create', short_help='creates a new NSD/NSpkg')
@click.argument('filename')
@click.option('--overwrite', default=None,
              help='overwrites some fields in NSD')
@click.pass_context
def nsd_create1(ctx, filename, overwrite):
    '''creates a new NSD/NSpkg

    FILENAME: NSD yaml file or NSpkg tar.gz file
    '''
    nsd_create(ctx, filename, overwrite)


@cli.command(name='nspkg-create', short_help='creates a new NSD/NSpkg')
@click.argument('filename')
@click.option('--overwrite', default=None,
              help='overwrites some fields in NSD')
@click.pass_context
def nsd_create2(ctx, filename, overwrite):
    '''creates a new NSD/NSpkg

    FILENAME: NSD yaml file or NSpkg tar.gz file
    '''
    nsd_create(ctx, filename, overwrite)


def vnfd_create(ctx, filename, overwrite):
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.vnfd.create(filename, overwrite)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='vnfd-create', short_help='creates a new VNFD/VNFpkg')
@click.argument('filename')
@click.option('--overwrite', default=None,
              help='overwrites some fields in VNFD')
@click.pass_context
def vnfd_create1(ctx, filename, overwrite):
    '''creates a new VNFD/VNFpkg

    FILENAME: VNFD yaml file or VNFpkg tar.gz file
    '''
    vnfd_create(ctx, filename, overwrite)


@cli.command(name='vnfpkg-create', short_help='creates a new VNFD/VNFpkg')
@click.argument('filename')
@click.option('--overwrite', default=None,
              help='overwrites some fields in VNFD')
@click.pass_context
def vnfd_create2(ctx, filename, overwrite):
    '''creates a new VNFD/VNFpkg

    FILENAME: VNFD yaml file or VNFpkg tar.gz file
    '''
    vnfd_create(ctx, filename, overwrite)


@cli.command(name='ns-create')
@click.option('--ns_name',
              prompt=True)
@click.option('--nsd_name',
              prompt=True)
@click.option('--vim_account',
              prompt=True)
@click.option('--admin_status',
              default='ENABLED',
              help='administration status')
@click.option('--ssh_keys',
              default=None,
              help='comma separated list of keys to inject to vnfs')
@click.option('--config',
              default=None,
              help='ns specific yaml configuration:\nvnf: [member-vnf-index: TEXT, vim_account: TEXT]\n'
              'vld: [name: TEXT, vim-network-name: TEXT or DICT with vim_account, vim_net entries]')
@click.pass_context
def ns_create(ctx,
              nsd_name,
              ns_name,
              vim_account,
              admin_status,
              ssh_keys,
              config):
    '''creates a new NS instance'''
    try:
        # if config:
        #     check_client_version(ctx.obj, '--config', 'v1')
        ctx.obj.ns.create(
            nsd_name,
            ns_name,
            config=config,
            ssh_keys=ssh_keys,
            account=vim_account)
    except ClientException as inst:
        print((inst.message))
        exit(1)

######################################### create 2 operation

    # def create2(self, nsd_name, ns_name, distribution=None,
    #           ssh_keys=None, description='default description',
    #           admin_status='ENABLED'):

@cli.command(name='ns-create2')
@click.option('--ns_name',
              prompt=True)
@click.option('--nsd_name',
              prompt=True)
@click.option('--admin_status',
              default='ENABLED',
              help='administration status')
@click.option('--ssh_keys',
              default=None,
              help='comma separated list of keys to inject to vnfs')
@click.option('--distribution',
              default=None,
              help='distribution of the vnfs in the different available vims')
@click.option('--config',
              default=None,
              help='kind of json object specifying the networks that requires to be created at the VIM for this NS')

@click.pass_context
def ns_create2(ctx,
              nsd_name,
              ns_name,
              admin_status,
              ssh_keys,
              distribution,
              config):
    '''creates a new NS instance accepting a VNF distribution'''
    try:
        # if config:
        #     check_client_version(ctx.obj, '--config', 'v1')
        ctx.obj.ns.create2(
            nsd_name,
            ns_name,
            distribution=distribution,
            config=config,
            ssh_keys=ssh_keys)
    except ClientException as inst:
        print((inst.message))
        exit(1)

########################################


####################
# UPDATE operations
####################

def nsd_update(ctx, name, content):
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.nsd.update(name, content)
    except ClientException as inst:
        print((inst.message))
        exit(1)

@cli.command(name='nsd-update', short_help='updates a NSD/NSpkg')
@click.argument('name')
@click.option('--content', default=None,
              help='filename with the NSD/NSpkg replacing the current one')
@click.pass_context
def nsd_update1(ctx, name, content):
    '''updates a NSD/NSpkg

    NAME: name or ID of the NSD/NSpkg
    '''
    nsd_update(ctx, name, content)


@cli.command(name='nspkg-update', short_help='updates a NSD/NSpkg')
@click.argument('name')
@click.option('--content', default=None,
              help='filename with the NSD/NSpkg replacing the current one')
@click.pass_context
def nsd_update2(ctx, name, content):
    '''updates a NSD/NSpkg

    NAME: name or ID of the NSD/NSpkg
    '''
    nsd_update(ctx, name, content)


def vnfd_update(ctx, name, content):
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.vnfd.update(name, content)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='vnfd-update', short_help='updates a new VNFD/VNFpkg')
@click.argument('name')
@click.option('--content', default=None,
              help='filename with the VNFD/VNFpkg replacing the current one')
@click.pass_context
def vnfd_update1(ctx, name, content):
    '''updates a VNFD/VNFpkg

    NAME: name or ID of the VNFD/VNFpkg
    '''
    vnfd_update(ctx, name, content)


@cli.command(name='vnfpkg-update', short_help='updates a VNFD/VNFpkg')
@click.argument('name')
@click.option('--content', default=None,
              help='filename with the VNFD/VNFpkg replacing the current one')
@click.pass_context
def vnfd_update2(ctx, name, content):
    '''updates a VNFD/VNFpkg

    NAME: VNFD yaml file or VNFpkg tar.gz file
    '''
    vnfd_update(ctx, name, content)


####################
# DELETE operations
####################

def nsd_delete(ctx, name, force):
    try:
        if not force:
            ctx.obj.nsd.delete(name)
        else:
            check_client_version(ctx.obj, '--force')
            ctx.obj.nsd.delete(name, force)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='nsd-delete', short_help='deletes a NSD/NSpkg')
@click.argument('name')
@click.option('--force', is_flag=True, help='forces the deletion bypassing pre-conditions')
@click.pass_context
def nsd_delete1(ctx, name, force):
    '''deletes a NSD/NSpkg

    NAME: name or ID of the NSD/NSpkg to be deleted
    '''
    nsd_delete(ctx, name, force)


@cli.command(name='nspkg-delete', short_help='deletes a NSD/NSpkg')
@click.argument('name')
@click.option('--force', is_flag=True, help='forces the deletion bypassing pre-conditions')
@click.pass_context
def nsd_delete2(ctx, name, force):
    '''deletes a NSD/NSpkg

    NAME: name or ID of the NSD/NSpkg to be deleted
    '''
    nsd_delete(ctx, name, force)


def vnfd_delete(ctx, name, force):
    try:
        if not force:
            ctx.obj.vnfd.delete(name)
        else:
            check_client_version(ctx.obj, '--force')
            ctx.obj.vnfd.delete(name, force)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='vnfd-delete', short_help='deletes a VNFD/VNFpkg')
@click.argument('name')
@click.option('--force', is_flag=True, help='forces the deletion bypassing pre-conditions')
@click.pass_context
def vnfd_delete1(ctx, name, force):
    '''deletes a VNFD/VNFpkg

    NAME: name or ID of the VNFD/VNFpkg to be deleted
    '''
    vnfd_delete(ctx, name, force)


@cli.command(name='vnfpkg-delete', short_help='deletes a VNFD/VNFpkg')
@click.argument('name')
@click.option('--force', is_flag=True, help='forces the deletion bypassing pre-conditions')
@click.pass_context
def vnfd_delete2(ctx, name, force):
    '''deletes a VNFD/VNFpkg

    NAME: name or ID of the VNFD/VNFpkg to be deleted
    '''
    vnfd_delete(ctx, name, force)


@cli.command(name='ns-delete', short_help='deletes a NS instance')
@click.argument('name')
@click.option('--force', is_flag=True, help='forces the deletion bypassing pre-conditions')
@click.pass_context
def ns_delete(ctx, name, force):
    '''deletes a NS instance

    NAME: name or ID of the NS instance to be deleted
    '''
    try:
        if not force:
            ctx.obj.ns.delete(name)
        else:
            check_client_version(ctx.obj, '--force')
            ctx.obj.ns.delete(name, force)
    except ClientException as inst:
        print((inst.message))
        exit(1)


####################
# VIM operations
####################
 
@cli.command(name='vim-create')
@click.option('--name',
              prompt=True,
              help='Name to create datacenter')
@click.option('--user',
              prompt=True,
              help='VIM username')
@click.option('--password',
              prompt=True,
              hide_input=True,
              confirmation_prompt=True,
              help='VIM password')
@click.option('--auth_url',
              prompt=True,
              help='VIM url')
@click.option('--tenant',
              prompt=True,
              help='VIM tenant name')
@click.option('--config',
              default=None,
              help='VIM specific config parameters')
@click.option('--account_type',
              default='openstack',
              help='VIM type')
@click.option('--description',
              default='no description',
              help='human readable description')
@click.option('--sdn_controller', default=None, help='Name or id of the SDN controller associated to this VIM account')
@click.option('--sdn_port_mapping', default=None, help="File describing the port mapping between compute nodes' ports and switch ports")
@click.pass_context
def vim_create(ctx,
               name,
               user,
               password,
               auth_url,
               tenant,
               config,
               account_type,
               description,
               sdn_controller,
               sdn_port_mapping):
    '''creates a new VIM account
    '''
    try:
        if sdn_controller:
            check_client_version(ctx.obj, '--sdn_controller')
        if sdn_port_mapping:
            check_client_version(ctx.obj, '--sdn_port_mapping')
        vim = {}
        vim['vim-username'] = user
        vim['vim-password'] = password
        vim['vim-url'] = auth_url
        vim['vim-tenant-name'] = tenant
        vim['vim-type'] = account_type
        vim['description'] = description
        vim['config'] = config
        if sdn_controller or sdn_port_mapping:
            ctx.obj.vim.create(name, vim, sdn_controller, sdn_port_mapping)
        else:
            ctx.obj.vim.create(name, vim)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='vim-update', short_help='updates a VIM account')
@click.argument('name')
@click.option('--newname', help='New name for the VIM account')
@click.option('--user', help='VIM username')
@click.option('--password', help='VIM password')
@click.option('--auth_url', help='VIM url')
@click.option('--tenant', help='VIM tenant name')
@click.option('--config', help='VIM specific config parameters')
@click.option('--account_type', help='VIM type')
@click.option('--description', help='human readable description')
@click.option('--sdn_controller', default=None, help='Name or id of the SDN controller associated to this VIM account')
@click.option('--sdn_port_mapping', default=None, help="File describing the port mapping between compute nodes' ports and switch ports")
@click.pass_context
def vim_update(ctx,
               name,
               newname,
               user,
               password,
               auth_url,
               tenant,
               config,
               account_type,
               description,
               sdn_controller,
               sdn_port_mapping):
    '''updates a VIM account

    NAME: name or ID of the VIM account
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name)
        vim = {}
        if newname: vim['name'] = newname
        if user: vim['vim_user'] = user
        if password: vim['vim_password'] = password
        if auth_url: vim['vim_url'] = auth_url
        if tenant: vim['vim-tenant-name'] = tenant
        if account_type: vim['vim_type'] = account_type
        if description: vim['description'] = description
        if config: vim['config'] = config
        ctx.obj.vim.update(name, vim, sdn_controller, sdn_port_mapping)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='vim-delete')
@click.argument('name')
@click.option('--force', is_flag=True, help='forces the deletion bypassing pre-conditions')
@click.pass_context
def vim_delete(ctx, name, force):
    '''deletes a VIM account

    NAME: name or ID of the VIM account to be deleted
    '''
    try:
        if not force:
            ctx.obj.vim.delete(name)
        else:
            check_client_version(ctx.obj, '--force')
            ctx.obj.vim.delete(name, force)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='vim-list')
@click.option('--ro_update/--no_ro_update',
              default=False,
              help='update list from RO')
@click.option('--filter', default=None,
              help='restricts the list to the VIM accounts matching the filter')
@click.pass_context
def vim_list(ctx, ro_update, filter):
    '''list all VIM accounts'''
    if filter:
        check_client_version(ctx.obj, '--filter')
    if ro_update:
        check_client_version(ctx.obj, '--ro_update', 'v1')
    fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
    if fullclassname == 'osmclient.sol005.client.Client':
        resp = ctx.obj.vim.list(filter)
    else:
        resp = ctx.obj.vim.list(ro_update)
    table = PrettyTable(['vim name', 'uuid'])
    for vim in resp:
        table.add_row([vim['name'], vim['uuid']])
    table.align = 'l'
    print(table)


@cli.command(name='vim-show')
@click.argument('name')
@click.pass_context
def vim_show(ctx, name):
    '''shows the details of a VIM account

    NAME: name or ID of the VIM account
    '''
    try:
        resp = ctx.obj.vim.get(name)
        if 'vim_password' in resp:
            resp['vim_password']='********'
    except ClientException as inst:
        print((inst.message))
        exit(1)

    table = PrettyTable(['key', 'attribute'])
    for k, v in list(resp.items()):
        table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


####################
# SDN controller operations
####################

@cli.command(name='sdnc-create')
@click.option('--name',
              prompt=True,
              help='Name to create sdn controller')
@click.option('--type',
              prompt=True,
              help='SDN controller type')
@click.option('--sdn_controller_version',
              help='SDN controller username')
@click.option('--ip_address',
              prompt=True,
              help='SDN controller IP address')
@click.option('--port',
              prompt=True,
              help='SDN controller port')
@click.option('--switch_dpid',
              prompt=True,
              help='Switch DPID (Openflow Datapath ID)')
@click.option('--user',
              help='SDN controller username')
@click.option('--password',
              hide_input=True,
              confirmation_prompt=True,
              help='SDN controller password')
#@click.option('--description',
#              default='no description',
#              help='human readable description')
@click.pass_context
def sdnc_create(ctx,
               name,
               type,
               sdn_controller_version,
               ip_address,
               port,
               switch_dpid,
               user,
               password):
    '''creates a new SDN controller
    '''
    sdncontroller = {}
    sdncontroller['name'] = name
    sdncontroller['type'] = type
    sdncontroller['ip'] = ip_address
    sdncontroller['port'] = int(port)
    sdncontroller['dpid'] = switch_dpid
    if sdn_controller_version:
        sdncontroller['version'] = sdn_controller_version
    if user:
        sdncontroller['user'] = user
    if password:
        sdncontroller['password'] = password
#    sdncontroller['description'] = description
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.sdnc.create(name, sdncontroller)
    except ClientException as inst:
        print((inst.message))


@cli.command(name='sdnc-update', short_help='updates an SDN controller')
@click.argument('name')
@click.option('--newname', help='New name for the SDN controller')
@click.option('--type', help='SDN controller type')
@click.option('--sdn_controller_version', help='SDN controller username')
@click.option('--ip_address', help='SDN controller IP address')
@click.option('--port', help='SDN controller port')
@click.option('--switch_dpid', help='Switch DPID (Openflow Datapath ID)')
@click.option('--user', help='SDN controller username')
@click.option('--password', help='SDN controller password')
#@click.option('--description',  default=None, help='human readable description')
@click.pass_context
def sdnc_update(ctx,
               name,
               newname,
               type,
               sdn_controller_version,
               ip_address,
               port,
               switch_dpid,
               user,
               password):
    '''updates an SDN controller

    NAME: name or ID of the SDN controller
    '''
    sdncontroller = {}
    if newname: sdncontroller['name'] = newname
    if type: sdncontroller['type'] = type
    if ip_address: sdncontroller['ip'] = ip_address
    if port: sdncontroller['port'] = int(port)
    if switch_dpid: sdncontroller['dpid'] = switch_dpid
#    sdncontroller['description'] = description
    if sdn_controller_version is not None:
        if sdn_controller_version=="":
            sdncontroller['version'] = None
        else:
            sdncontroller['version'] = sdn_controller_version
    if user is not None:
        if user=="":
            sdncontroller['user'] = None
        else:
            sdncontroller['user'] = user
    if password is not None:
        if password=="":
            sdncontroller['password'] = None
        else:
            sdncontroller['password'] = user
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.sdnc.update(name, sdncontroller)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='sdnc-delete')
@click.argument('name')
@click.option('--force', is_flag=True, help='forces the deletion bypassing pre-conditions')
@click.pass_context
def sdnc_delete(ctx, name, force):
    '''deletes an SDN controller

    NAME: name or ID of the SDN controller to be deleted
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.sdnc.delete(name, force)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='sdnc-list')
@click.option('--filter', default=None,
              help='restricts the list to the SDN controllers matching the filter')
@click.pass_context
def sdnc_list(ctx, filter):
    '''list all SDN controllers'''
    try:
        check_client_version(ctx.obj, ctx.command.name)
        resp = ctx.obj.sdnc.list(filter)
    except ClientException as inst:
        print((inst.message))
        exit(1)
    table = PrettyTable(['name', 'id'])
    for sdnc in resp:
        table.add_row([sdnc['name'], sdnc['_id']])
    table.align = 'l'
    print(table)


@cli.command(name='sdnc-show')
@click.argument('name')
@click.pass_context
def sdnc_show(ctx, name):
    '''shows the details of an SDN controller

    NAME: name or ID of the SDN controller
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name)
        resp = ctx.obj.sdnc.get(name)
    except ClientException as inst:
        print((inst.message))
        exit(1)

    table = PrettyTable(['key', 'attribute'])
    for k, v in list(resp.items()):
        table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


####################
# Fault Management operations
####################

@cli.command(name='ns-alarm-create')
@click.argument('name')
@click.option('--ns', prompt=True, help='NS instance id or name')
@click.option('--vnf', prompt=True,
              help='VNF name (VNF member index as declared in the NSD)')
@click.option('--vdu', prompt=True,
              help='VDU name (VDU name as declared in the VNFD)')
@click.option('--metric', prompt=True,
              help='Name of the metric (e.g. cpu_utilization)')
@click.option('--severity', default='WARNING',
              help='severity of the alarm (WARNING, MINOR, MAJOR, CRITICAL, INDETERMINATE)')
@click.option('--threshold_value', prompt=True,
              help='threshold value that, when crossed, an alarm is triggered')
@click.option('--threshold_operator', prompt=True,
              help='threshold operator describing the comparison (GE, LE, GT, LT, EQ)')
@click.option('--statistic', default='AVERAGE',
              help='statistic (AVERAGE, MINIMUM, MAXIMUM, COUNT, SUM)')
@click.pass_context
def ns_alarm_create(ctx, name, ns, vnf, vdu, metric, severity,
                    threshold_value, threshold_operator, statistic):
    '''creates a new alarm for a NS instance'''
    ns_instance = ctx.obj.ns.get(ns)
    alarm = {}
    alarm['alarm_name'] = name
    alarm['ns_id'] = ns_instance['_id']
    alarm['correlation_id'] = ns_instance['_id']
    alarm['vnf_member_index'] = vnf
    alarm['vdu_name'] = vdu
    alarm['metric_name'] = metric
    alarm['severity'] = severity
    alarm['threshold_value'] = int(threshold_value)
    alarm['operation'] = threshold_operator
    alarm['statistic'] = statistic
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.ns.create_alarm(alarm)
    except ClientException as inst:
        print((inst.message))
        exit(1)


#@cli.command(name='ns-alarm-delete')
#@click.argument('name')
#@click.pass_context
#def ns_alarm_delete(ctx, name):
#    '''deletes an alarm
#
#    NAME: name of the alarm to be deleted
#    '''
#    try:
#        check_client_version(ctx.obj, ctx.command.name)
#        ctx.obj.ns.delete_alarm(name)
#    except ClientException as inst:
#        print(inst.message)
#        exit(1)


####################
# Performance Management operations
####################

@cli.command(name='ns-metric-export')
@click.option('--ns', prompt=True, help='NS instance id or name')
@click.option('--vnf', prompt=True,
              help='VNF name (VNF member index as declared in the NSD)')
@click.option('--vdu', prompt=True,
              help='VDU name (VDU name as declared in the VNFD)')
@click.option('--metric', prompt=True,
              help='name of the metric (e.g. cpu_utilization)')
#@click.option('--period', default='1w',
#              help='metric collection period (e.g. 20s, 30m, 2h, 3d, 1w)')
@click.option('--interval', help='periodic interval (seconds) to export metrics continuously')
@click.pass_context
def ns_metric_export(ctx, ns, vnf, vdu, metric, interval):
    '''exports a metric to the internal OSM bus, which can be read by other apps
    '''
    ns_instance = ctx.obj.ns.get(ns)
    metric_data = {}
    metric_data['ns_id'] = ns_instance['_id']
    metric_data['correlation_id'] = ns_instance['_id']
    metric_data['vnf_member_index'] = vnf
    metric_data['vdu_name'] = vdu
    metric_data['metric_name'] = metric
    metric_data['collection_unit'] = 'WEEK'
    metric_data['collection_period'] = 1
    try:
        check_client_version(ctx.obj, ctx.command.name)
        if not interval:
            print('{}'.format(ctx.obj.ns.export_metric(metric_data)))
        else:
            i = 1
            while True:
                print('{} {}'.format(ctx.obj.ns.export_metric(metric_data),i))
                time.sleep(int(interval))
                i+=1
    except ClientException as inst:
        print((inst.message))
        exit(1)


####################
# Other operations
####################

@cli.command(name='upload-package')
@click.argument('filename')
@click.pass_context
def upload_package(ctx, filename):
    '''uploads a VNF package or NS package

    FILENAME: VNF or NS package file (tar.gz)
    '''
    try:
        ctx.obj.package.upload(filename)
        fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
        if fullclassname != 'osmclient.sol005.client.Client':
            ctx.obj.package.wait_for_upload(filename)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='ns-scaling-show')
@click.argument('ns_name')
@click.pass_context
def show_ns_scaling(ctx, ns_name):
    '''shows the status of a NS scaling operation

    NS_NAME: name of the NS instance being scaled
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name, 'v1')
        resp = ctx.obj.ns.list()
    except ClientException as inst:
        print((inst.message))
        exit(1)

    table = PrettyTable(
        ['group-name',
         'instance-id',
         'operational status',
         'create-time',
         'vnfr ids'])

    for ns in resp:
        if ns_name == ns['name']:
            nsopdata = ctx.obj.ns.get_opdata(ns['id'])
            scaling_records = nsopdata['nsr:nsr']['scaling-group-record']
            for record in scaling_records:
                if 'instance' in record:
                    instances = record['instance']
                    for inst in instances:
                        table.add_row(
                            [record['scaling-group-name-ref'],
                             inst['instance-id'],
                                inst['op-status'],
                                time.strftime('%Y-%m-%d %H:%M:%S',
                                              time.localtime(
                                                  inst['create-time'])),
                                inst['vnfrs']])
    table.align = 'l'
    print(table)


@cli.command(name='ns-scale')
@click.argument('ns_name')
@click.option('--ns_scale_group', prompt=True)
@click.option('--index', prompt=True)
@click.pass_context
def ns_scale(ctx, ns_name, ns_scale_group, index):
    '''scales NS

    NS_NAME: name of the NS instance to be scaled
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name, 'v1')
        ctx.obj.ns.scale(ns_name, ns_scale_group, index)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='config-agent-list')
@click.pass_context
def config_agent_list(ctx):
    '''list config agents'''
    try:
        check_client_version(ctx.obj, ctx.command.name, 'v1')
    except ClientException as inst:
        print((inst.message))
        exit(1)
    table = PrettyTable(['name', 'account-type', 'details'])
    for account in ctx.obj.vca.list():
        table.add_row(
            [account['name'],
             account['account-type'],
             account['juju']])
    table.align = 'l'
    print(table)


@cli.command(name='config-agent-delete')
@click.argument('name')
@click.pass_context
def config_agent_delete(ctx, name):
    '''deletes a config agent

    NAME: name of the config agent to be deleted
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name, 'v1')
        ctx.obj.vca.delete(name)
    except ClientException as inst:
        print((inst.message))
        exit(1)


@cli.command(name='config-agent-add')
@click.option('--name',
              prompt=True)
@click.option('--account_type',
              prompt=True)
@click.option('--server',
              prompt=True)
@click.option('--user',
              prompt=True)
@click.option('--secret',
              prompt=True,
              hide_input=True,
              confirmation_prompt=True)
@click.pass_context
def config_agent_add(ctx, name, account_type, server, user, secret):
    '''adds a config agent'''
    try:
        check_client_version(ctx.obj, ctx.command.name, 'v1')
        ctx.obj.vca.create(name, account_type, server, user, secret)
    except ClientException as inst:
        print((inst.message))
        exit(1)

@cli.command(name='ro-dump')
@click.pass_context
def ro_dump(ctx):
    '''shows RO agent information'''
    check_client_version(ctx.obj, ctx.command.name, 'v1')
    resp = ctx.obj.vim.get_resource_orchestrator()
    table = PrettyTable(['key', 'attribute'])
    for k, v in list(resp.items()):
        table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='vcs-list')
@click.pass_context
def vcs_list(ctx):
    check_client_version(ctx.obj, ctx.command.name, 'v1')
    resp = ctx.obj.utils.get_vcs_info()
    table = PrettyTable(['component name', 'state'])
    for component in resp:
        table.add_row([component['component_name'], component['state']])
    table.align = 'l'
    print(table)


@cli.command(name='ns-action')
@click.argument('ns_name')
@click.option('--vnf_name', default=None)
@click.option('--action_name', prompt=True)
@click.option('--params', prompt=True)
@click.pass_context
def ns_action(ctx,
              ns_name,
              vnf_name,
              action_name,
              params):
    '''executes an action/primitive over a NS instance

    NS_NAME: name or ID of the NS instance
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name)
        op_data={}
        if vnf_name:
            op_data['vnf_member_index'] = vnf_name
        op_data['primitive'] = action_name
        op_data['primitive_params'] = yaml.load(params)
        ctx.obj.ns.exec_op(ns_name, op_name='action', op_data=op_data)

    except ClientException as inst:
        print((inst.message))
        exit(1)


if __name__ == '__main__':
    cli()
