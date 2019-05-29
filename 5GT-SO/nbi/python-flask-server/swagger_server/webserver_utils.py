# Author: Luca Vettori
# Copyright (C) 2018 CTTC/CERCA
# License: To be defined. Currently use is restricted to partners of the 5G-Transformer project,
#          http://5g-transformer.eu/, no use or redistribution of any kind outside the 5G-Transformer project is
#          allowed.
# Disclaimer: this software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
import collections
import json
import os
import shutil
import tarfile

import networkx as nx
import yaml
from networkx.readwrite import json_graph
from pprint import pprint
from db.nsd_db import nsd_db
from db.nsir_db import nsir_db
from db.ns_db import ns_db
from nbi import log_queue


def selected_node(graph, name):
    """
    Method to select a specific node inside of the graph with name and type as key of node itself
    :param graph: nx.Graph()
    :param name: input value to be searched in the graph nodes
    :return: the first (in theory the only one) index of node with corresponding name index or the length of graph
    """
    select_node = [n for n, v in graph.nodes(data=True) if v['name'] == name]
    if not select_node:
        # print(graph.nodes, graph.number_of_nodes())
        # return graph.number_of_nodes()
        if not graph.nodes:
            # in case of empty graph
            return 0
        else:
            # return the index of the "last" node + 1, in order to avoid some "hole" problem in graph indexing
            return list(graph.nodes)[-1] + 1
    else:
        return select_node[0]


def add_placement(graph, placement_info):
    """
    Return the node-link format of the NS Descriptor
    :param graph: nx graph representing the NS (actually is nsd)
    :param placement_info: placement info
    :return: json graph format to be handled by D3 Javascript Element in rendered html page
    """
    # add label "placement_element" (related to PoPs) to VNF nodes
    for used_nfvipop in placement_info['usedNFVIPops']:
        for node in graph:
            if graph.nodes[node]['type'] == 'VNFD' and graph.nodes[node]['name'] in used_nfvipop['mappedVNFs']:
                graph.nodes[node]['placement_element'] = ["PoP_" + used_nfvipop['NFVIPoPID']]
    # add label "placement_element" (related to PoPs) to VLD nodes
    for used_vl in placement_info['usedVLs']:
        for node in graph:
            if graph.nodes[node]['type'] == 'VLD' and graph.nodes[node]['name'] in used_vl['mappedVLs']:
                # adding shared placement info in attribute of node of graph as list
                if 'placement_element' in graph.nodes[node]:
                    if not "PoP_" + used_vl['NFVIPoPID'] in graph.nodes[node]['placement_element']:
                        graph.nodes[node]['placement_element'].append("PoP_" + used_vl['NFVIPoPID'])
                else:
                    graph.nodes[node]['placement_element'] = ["PoP_" + used_vl['NFVIPoPID']]
                # graph.nodes[node]['placement_element'] = "PoP_" + used_vl['NFVIPoPID']
    # add label "placement_element" (related to LLs) to VLD nodes
    for used_ll in placement_info['usedLLs']:
        for node in graph:
            if graph.nodes[node]['type'] == 'VLD' and graph.nodes[node]['name'] in used_ll['mappedVLs']:
                graph.nodes[node]['placement_element'] = ["LLID_" + used_ll['LLID']]

    return graph


def abstracted_view_from_json(pops, fed_pops, lls):
    """
    Return the node-link format of the Abstracted view of MTP
    :param pops: list of nfvipops (json)
    :param fed_pops: list of federated nfvipops
    :param lls: list of logical links (json)
    :return: json graph format to be handled by D3 Javascript Element in rendered html page
    """
    # create a nx.MultiGraph (allow to have multiple links between the same 2 nodes
    g = nx.MultiGraph()
    # dealing with NfviPops
    for pop in pops:
        current_node_id = g.number_of_nodes()
        # add a node to nx.Graph for every NFVI POP
        for resource_zone_attribute in pop['nfviPopAttributes']['resourceZoneAttributes']:
            # ASSUMPTION: 1 ZONEID FOR NFVIPOP TODO CHECK
            g.add_node(current_node_id,
                       name=pop['nfviPopAttributes']['nfviPopId'],
                       zone_id=resource_zone_attribute['zoneId'],
                       zone_name=resource_zone_attribute['zoneName'],
                       gateway=pop['nfviPopAttributes']['networkConnectivityEndpoint'][0]['netGwIpAddress'],
                       geo_location=pop['nfviPopAttributes']['geographicalLocationInfo'],
                       type="NFVIPOP",
                       img="static/images/pop5.png",
                       group=1)
            for i, network_ce in enumerate(pop['nfviPopAttributes']['networkConnectivityEndpoint']):
                g.add_node(current_node_id + i + 1,
                           name=network_ce['netGwIpAddress'],
                           type="GATEWAY",
                           img="static/images/router.png",
                           group=2)
                g.add_edge(current_node_id, current_node_id+i+1, length=20)
    # dealing with Federated NfviPops
    for fed_pop in fed_pops:
        current_node_id = g.number_of_nodes()
        g.add_node(current_node_id,
                   name=fed_pop['nfviPopAttributes']['nfviPopId'],
                   geo_location=fed_pop['nfviPopAttributes']['geographicalLocationInfo'],
                   type="NFVIPOP-Fed",
                   img="static/images/pop_fed.png",
                   group=1)
        for i, network_ce in enumerate(fed_pop['nfviPopAttributes']['networkConnectivityEndpoint']):
            g.add_node(current_node_id+i+1,
                       name=network_ce['netGwIpAddress'],
                       type="GATEWAY",
                       img="static/images/router.png",
                       group=2)
            g.add_edge(current_node_id, current_node_id+i+1, length=20)
    # dealing with Logical Links
    for ll in lls:
        replicated = False
        source_node = -1
        destination_node = -1
        for node in g:
            # print(g.nodes[node]['gateway'])
            if g.nodes[node]['type'] == "GATEWAY" and g.nodes[node]["name"] == ll['logicalLinks']['srcGwIpAddress']:
                source_node = node
            # if 'gateway' in g.nodes[node] and g.nodes[node]['gateway'] == ll['logicalLinks']['srcGwIpAddress']:
            #     source_node = node
            if g.nodes[node]['type'] == "GATEWAY" and g.nodes[node]["name"] == ll['logicalLinks']['dstGwIpAddress']:
                destination_node = node
            # if 'gateway' in g.nodes[node] and g.nodes[node]['gateway'] == ll['logicalLinks']['dstGwIpAddress']:
            #     destination_node = node
        # if case there is an edge
        if source_node != -1 and destination_node != -1:
            # not displaying one of 2 bidirectional links
            # TODO Added using llid_f and llid_b to distinguish both directions of LL
            for i, o, e in g.edges(data=True):
                # if 'llid' in e and e['llid'] == ll.logical_links.logical_link_id:  # TODO added
                if 'llid' in e and e['llid'] == ll['logicalLinks']['logicalLinkId'].split("_")[0]:  # TODO added
                    replicated = True
            if not replicated:
                g.add_edge(source_node,
                           destination_node,
                           # llid=ll.logical_links.logical_link_id,
                           llid=ll['logicalLinks']['logicalLinkId'].split("_")[0],   # TODO added
                           length=200)

    return json_graph.node_link_data(g)  # node-link format to serialize


def ifa014_conversion(descriptor):
    """
    ifa014 nsd to osm nsd
    :param descriptor: json object representing the NS descriptor following the IFA014 standard
    :return: list of json objects representing the NS descriptors following OSM standard and index of default nsd
    """
    ifa014_nsd = descriptor['nsd']
    list_of_json_nsd_osm = []
    index_default_nsd = None
    for i_ns_df, ns_df in enumerate(ifa014_nsd['nsDf']):
        for ns_level_id in ns_df['nsInstantiationLevel']:
            json_nsd_osm = dict()
            json_nsd_osm['nsd:nsd-catalog'] = dict()
            json_nsd_osm['nsd:nsd-catalog']['nsd'] = list()
            nsd_list_element = dict()
            nsd_list_element['id'] = "{}_{}_{}".format(ifa014_nsd['nsdIdentifier'], ns_df['nsDfId'], ns_level_id['nsLevelId'])
            nsd_list_element['name'] = "{}_{}_{}".format(ifa014_nsd['nsdIdentifier'], ns_df['nsDfId'], ns_level_id['nsLevelId'])
            nsd_list_element['short-name'] = ifa014_nsd['nsdName']
            nsd_list_element['vendor'] = ifa014_nsd['designer'] + '-CTTC'
            nsd_list_element['version'] = ifa014_nsd['version']
            nsd_list_element['vld'] = list()
            nsd_list_element['constituent-vnfd'] = list()
            # retrieve the index of default nsd
            if i_ns_df == 0 and ns_level_id['nsLevelId'] == ns_df['defaultNsInstantiationLevelId']:
                index_default_nsd = len(list_of_json_nsd_osm)
            nsd_list_element['description'] = ns_level_id.get('description',
                                                              'Default description from IFA014/OSM nsd conversion')
            for virtualLink in ns_level_id['virtualLinkToLevelMapping']:
                vld = dict()
                for virtualLinkProfile in ns_df['virtualLinkProfile']:
                    if virtualLinkProfile['virtualLinkProfileId'] == virtualLink['virtualLinkProfileId']:
                        vld['virtualLinkProfileId'] = virtualLinkProfile['virtualLinkProfileId']  # To be removed at the end
                        vld['id'] = virtualLinkProfile['virtualLinkDescId']
                        vld['name'] = virtualLinkProfile['virtualLinkDescId']
                        vld['short-name'] = virtualLinkProfile['virtualLinkDescId']
                        vld['vim-network-name'] = virtualLinkProfile['virtualLinkDescId']
                # vld['vendor'] = virtualLink['virtualLinkDescProvider'] + '-CTTC'
                # vld['description'] = virtualLink['description']
                # vld['version'] = virtualLink['virtuaLinkDescVersion']
                vld['type'] = 'ELAN'  # TBD
                # vld['root-bandwidth'] = virtualLink['bitRateRequirements']['root']
                # vld['leaf-bandwidth'] = virtualLink['bitRateRequirements']['leaf']
                vld['mgmt-network'] = 'true'  # TBD how to choose true
                vld['vnfd-connection-point-ref'] = list()
                nsd_list_element['vld'].append(vld)
            for i, vnf in enumerate(ns_level_id['vnfToLevelMapping']):
                index = int(vnf['numberOfInstances'])
                for x in range(0, index):
                    for vnfProfile in ns_df['vnfProfile']:
                        if vnfProfile['vnfProfileId'] == vnf['vnfProfileId']:
                            index_of_constituent_vnfd = len(nsd_list_element['constituent-vnfd']) + 1
                            nsd_list_element['constituent-vnfd'].append({'vnfd-id-ref': vnfProfile['vnfdId'],
                                                                         'member-vnf-index':
                                                                             str(index_of_constituent_vnfd)})
                            for vl in nsd_list_element['vld']:
                                for nsVirtualLinkConn in vnfProfile['nsVirtualLinkConnectivity']:
                                    if vl['virtualLinkProfileId'] == nsVirtualLinkConn['virtualLinkProfileId']:
                                        vl['vnfd-connection-point-ref'].append({
                                            'vnfd-id-ref': vnfProfile['vnfdId'],
                                            'member-vnf-index-ref': str(index_of_constituent_vnfd),
                                            'vnfd-connection-point-ref': nsVirtualLinkConn['cpdId'][0]})
            # remove the virtualLinkProfileId attribute in vld (used to simplify the process)
            for vld in nsd_list_element['vld']:
                vld.pop("virtualLinkProfileId")
            # sap part
            # TODO To be verified
            nsd_list_element['connection-point'] = list()
            for sapd in ifa014_nsd['sapd']:
                if sapd['addressData'][0]['floatingIpActivated']:  # should be boolean
                    for vld in nsd_list_element['vld']:
                        if vld['id'] == sapd['nsVirtualLinkDescId']:
                            # vld['mgmt-network'] = sapd['addressData'][0]['management']
                            for index_sap, vnf_connection_point_ref in enumerate(vld['vnfd-connection-point-ref']):
                                nsd_list_element['connection-point'].append({"name": sapd['cpdId'] + "_" + str(index_sap),
                                                                             "type": "VPORT",
                                                                             "floating-ip-required": True,
                                                                             "member-vnf-index-ref": vnf_connection_point_ref['member-vnf-index-ref'],
                                                                             "vnfd-connection-point-ref": vnf_connection_point_ref['vnfd-connection-point-ref'],
                                                                             "vnfd-id-ref": vnf_connection_point_ref['vnfd-id-ref']
                                                                             })
            json_nsd_osm['nsd:nsd-catalog']['nsd'].append(nsd_list_element)
            list_of_json_nsd_osm.append(json_nsd_osm)
    return list_of_json_nsd_osm, index_default_nsd


def ifa011_conversion(descriptor):
    """
    ifa011 vnfd to osm vnfd
    :param descriptor: json object representing the VNFD descriptor following the IFA011 standard
    :return: json object representing the NS descriptor following OSM standard and name of yaml nsd
    """
    ifa011_vnfd = descriptor

    json_vnfd_osm = dict()
    json_vnfd_osm['vnfd:vnfd-catalog'] = dict()
    json_vnfd_osm['vnfd:vnfd-catalog']['vnfd'] = list()
    vnfd_list_element = dict()
    vnfd_list_element['id'] = ifa011_vnfd['vnfdId']
    vnfd_list_element['name'] = ifa011_vnfd['vnfdId']
    vnfd_list_element['short-name'] = ifa011_vnfd['vnfdId']
    vnfd_list_element['vendor'] = ifa011_vnfd['vnfProvider'] + '-CTTC'
    vnfd_list_element['description'] = ifa011_vnfd['vnfProductInfoDescription']
    vnfd_list_element['version'] = ifa011_vnfd['vnfdVersion']
    vnfd_list_element['connection-point'] = list()
    vnfd_list_element['vdu'] = list()
    vnfd_list_element['mgmt-interface'] = dict()

    for extCp in ifa011_vnfd['vnfExtCpd']:
        external_cpdict = dict()
        external_cpdict['name'] = extCp['cpdId']
        if 'layerProtocol' in extCp and str(extCp['layerProtocol']).upper() == 'IPV4':
            external_cpdict['type'] = 'VPORT'
            if 'management' in extCp['addressData'][0] and extCp['addressData'][0]['management'] is True:
                vnfd_list_element['mgmt-interface']['cp'] = extCp['cpdId']
        vnfd_list_element['connection-point'].append(external_cpdict)

    instantiation_level_id = ifa011_vnfd['deploymentFlavour'][0]['instantiationLevel'][0]
    # print(instantiation_level_id)
    for vduLevel in instantiation_level_id['vduLevel']:
        count = int(vduLevel['numberOfInstances'])
        for vdu in ifa011_vnfd['vdu']:
            if vdu['vduId'] == vduLevel['vduId']:
                vm_flavour = dict()
                interface = list()
                for virtualComputeDesc in ifa011_vnfd['virtualComputeDesc']:
                    if virtualComputeDesc['virtualComputeDescId'] == vdu['virtualComputeDesc']:
                        vm_flavour['vcpu-count'] = str(virtualComputeDesc['virtualCpu']['numVirtualCpu'])
                        vm_flavour['memory-mb'] = str(virtualComputeDesc['virtualMemory']['virtualMemSize'] * 1024)
                for virtualStorageDesc in ifa011_vnfd['virtualStorageDesc']:
                    if virtualStorageDesc['id'] == vdu['virtualStorageDesc'][0]:
                        vm_flavour['storage-gb'] = str(virtualStorageDesc['sizeOfStorage'])
                # intCpd part
                for intCpd in vdu['intCpd']:
                    internal_interface = dict()
                    for i, external_interface in enumerate(ifa011_vnfd['vnfExtCpd']):
                        if external_interface['intCpd'] == intCpd['cpdId']:
                            internal_interface['name'] = intCpd['cpdId']
                            internal_interface['position'] = i
                            internal_interface['type'] = 'EXTERNAL'
                            internal_interface['virtual-interface'] = {'type': 'VIRTIO'}
                            internal_interface['external-connection-point-ref'] = external_interface['cpdId']
                    interface.append(internal_interface)
                # TODO verify IFA last version is ok with code below (08/03/2019)
                # swImageDesc part
                # sw_image = ''
                # for swImageDesc in ifa011_vnfd['swImageDesc']:
                #     if vdu['swImageDesc'] == swImageDesc['id']:
                #         sw_image = swImageDesc['swImage']
                # pprint(vdu)
                vnfd_list_element['vdu'].append({'id': vdu['vduId'],
                                                 'name': vdu['name'],
                                                 'description': vdu['description'],
                                                 'image': vdu['swImageDesc']['swImage'],  # TODO verify IFA last version is ok with code below (08/03/2019)
                                                 # 'image': sw_image,  #
                                                 'count': str(count),
                                                 'vm-flavor': vm_flavour,
                                                 'interface': interface})
    # TODO : review the following scaling part
    if 'scalingAspect' in ifa011_vnfd['deploymentFlavour'][0]:
        if ifa011_vnfd['deploymentFlavour'][0]['scalingAspect']:
            vnfd_list_element['scaling-group-descriptor'] = list()
            scaling_aspect = ifa011_vnfd['deploymentFlavour'][0]['scalingAspect'][0]
            scaling_policy = [{"name": scaling_aspect['id'],
                               "scaling-type": "manual",
                               "threshold-time": 10,
                               "cooldown-time": 120}]
            scaling_vdu = [{"vdu-id-ref": ifa011_vnfd['deploymentFlavour'][0]['vduProfile'][0]['vduId'],
                            "count": 1}]
            vnfd_list_element['scaling-group-descriptor'].append({
                "name": scaling_aspect['id']+'manual',
                "min-instance-count": 0,
                "max-instance-count": scaling_aspect['maxScaleLevel'],
                "scaling-policy": scaling_policy,
                "vdu": scaling_vdu
            })
    json_vnfd_osm['vnfd:vnfd-catalog']['vnfd'].append(vnfd_list_element)
    return json_vnfd_osm


def composite_desc_conversion(descriptor):
    """
    composite nsd to osm nsd
    :param descriptor: json object representing the NS descriptor following the composited 5GT standard
    :return: list of json objects representing the NS descriptors following OSM standard and index of default nsd
    """
    composite_nsd = descriptor['nsd']
    list_of_json_nsd_osm = []
    index_default_nsd = None
    for i_ns_df, ns_df in enumerate(composite_nsd['nsDf']):
        for ns_level_id in ns_df['nsInstantiationLevel']:
            json_nsd_osm = dict()
            json_nsd_osm['nsd:nsd-catalog'] = dict()
            json_nsd_osm['nsd:nsd-catalog']['nsd-composite'] = list()
            nsd_list_element = dict()
            # nsd_list_element['id'] = "{}".format(ns_level_id['nsLevelId'])
            nsd_list_element['id'] = "{}_{}_{}".format(composite_nsd['nsdIdentifier'], ns_df['nsDfId'], ns_level_id['nsLevelId'])
            # nsd_list_element['name'] = "{}".format(ns_level_id['nsLevelId'])
            nsd_list_element['name'] = "{}_{}_{}".format(composite_nsd['nsdIdentifier'], ns_df['nsDfId'], ns_level_id['nsLevelId'])
            nsd_list_element['short-name'] = composite_nsd['nsdName']
            nsd_list_element['vendor'] = composite_nsd['designer'] + '-CTTC'
            nsd_list_element['version'] = composite_nsd['version']
            nsd_list_element['vld'] = list()
            nsd_list_element['constituent-nsd'] = list()
            # retrieve the index of default nsd
            if i_ns_df == 0 and ns_level_id['nsLevelId'] == ns_df['defaultNsInstantiationLevelId']:
                index_default_nsd = len(list_of_json_nsd_osm)
            nsd_list_element['description'] = ns_level_id.get('description',
                                                              'Default description from composite/osm nsd conversion')
            for ns_to_level_mapping in ns_level_id['nsToLevelMapping']:
                # print("nsToLevelMapping[nsProfileId]: {}".format(ns_to_level_mapping['nsProfileId']))
                number_of_ns_instances = int(ns_to_level_mapping['numberOfInstances'])
                for x in range(0, number_of_ns_instances):
                    for ns_profile in ns_df['nsProfile']:
                        if ns_to_level_mapping['nsProfileId'] == ns_profile['nsProfileId']:
                            # vld part
                            for virtualLink in ns_profile['nsVirtualLinkConnectivity']:
                                vld = dict()
                                for virtualLinkProfile in ns_df['virtualLinkProfile']:
                                    if virtualLinkProfile['virtualLinkProfileId'] == virtualLink['virtualLinkProfileId']:
                                        vld['virtualLinkProfileId'] = virtualLinkProfile['virtualLinkProfileId']  # To be removed at the end
                                        vld['id'] = virtualLinkProfile['virtualLinkDescId']
                                        vld['name'] = virtualLinkProfile['virtualLinkDescId']
                                        vld['short-name'] = virtualLinkProfile['virtualLinkDescId']
                                vld['type'] = 'ELAN'  # TBD
                                vld['mgmt-network'] = 'false'  # TBD how to choose true
                                vld['nsd-connection-point-ref'] = list()
                                if not [element for element in nsd_list_element['vld'] if element['virtualLinkProfileId'] == vld['virtualLinkProfileId']]:
                                    nsd_list_element['vld'].append(vld)
                                # print(nsd_list_element['vld'])
                            # constituent-nsd part
                            index_of_constituent_nsd = len(nsd_list_element['constituent-nsd']) + 1
                            nsd_list_element['constituent-nsd'].append({'nsd-id-ref': "{}_{}_{}".
                                                                       format(ns_profile['nsdId'],
                                                                              ns_profile['nsDfId'],
                                                                              ns_profile['nsInstantiationLevelId']),
                                                                        'nested-nsd-id': "{}".format(ns_profile['nsdId']),
                                                                        'nested-ns-df-id': "{}".format(ns_profile['nsDfId']),
                                                                        'nested-ns-inst-level-id': "{}".format(ns_profile['nsInstantiationLevelId']),
                                                                        'member-ns-index':
                                                                            str(index_of_constituent_nsd)})
                            for vl in nsd_list_element['vld']:
                                for nsVirtualLinkConn in ns_profile['nsVirtualLinkConnectivity']:
                                    if vl['virtualLinkProfileId'] == nsVirtualLinkConn['virtualLinkProfileId']:
                                        vl['nsd-connection-point-ref'].append({
                                            'nsd-id-ref': "{}_{}_{}".format(ns_profile['nsdId'],
                                                                            ns_profile['nsDfId'],
                                                                            ns_profile['nsInstantiationLevelId']),
                                            'nested-nsd-id': "{}".format(ns_profile['nsdId']),
                                            'nested-ns-df-id': "{}".format(ns_profile['nsDfId']),
                                            'nested-ns-inst-level-id': "{}".format(ns_profile['nsInstantiationLevelId']),
                                            'member-ns-index-ref': str(index_of_constituent_nsd),
                                            'nsd-connection-point-ref': nsVirtualLinkConn['cpdId'][0]})

            # sap part
            # TODO To be verified
            # nsd_list_element['connection-point'] = list()
            # for sapd in ifa014_nsd['sapd']:
            #     if sapd['addressData'][0]['floatingIpActivated']:  # should be boolean
            #         for vld in nsd_list_element['vld']:
            #             if vld['id'] == sapd['nsVirtualLinkDescId']:
            #                 vld['mgmt-network'] = sapd['addressData'][0]['management']
            #                 for index_sap, vnf_connection_point_ref in enumerate(vld['vnfd-connection-point-ref']):
            #                     nsd_list_element['connection-point'].append({"name": sapd['cpdId'] + "_" + str(index_sap),
            #                                                                  "type": "VPORT",
            #                                                                  "floating-ip-required": True,
            #                                                                  "member-vnf-index-ref": vnf_connection_point_ref['member-vnf-index-ref'],
            #                                                                  "vnfd-connection-point-ref": vnf_connection_point_ref['vnfd-connection-point-ref'],
            #                                                                  "vnfd-id-ref": vnf_connection_point_ref['vnfd-id-ref']
            #                                                                  })

            json_nsd_osm['nsd:nsd-catalog']['nsd-composite'].append(nsd_list_element)
            # pprint(json_nsd_osm)
            list_of_json_nsd_osm.append(json_nsd_osm)
    return list_of_json_nsd_osm, index_default_nsd


def json_network_composite_ns(descriptor, ns_id=None):
    """
    Return the node-link format of the YAML NS Composite Instance
    :param descriptor: yaml object representing the NS composite descriptor
    :param ns_id: ns_id (useful to visualize the NSD instance
    :return: nx json graph format
    """
    # retrieve the list of nested ns id for placement info
    list_of_nested_ns_id = []
    ns_table_entry = ns_db.get_ns_record(ns_id)
    if 'nestedNsId' in ns_table_entry:
        # ASSUMPTION: ONLY ONE NSID IN THIS COLUMN
        list_of_nested_ns_id.append({"nsd_id": ns_db.get_nsdId(ns_table_entry['nestedNsId']),
                                     "ns_id": ns_table_entry['nestedNsId'],
                                     # ASSUMPTION: instantiate a composite service from a "local" nested service
                                     "federated_domain": "local"})
    if 'nested_service_info' in ns_table_entry:
        for nested_id in ns_table_entry['nested_service_info']:
            list_of_nested_ns_id.append({"nsd_id": nested_id['nested_id'],
                                         "ns_id": nested_id['nested_instance_id'],
                                         "federated_domain": nested_id['domain']})
    else:
        # TODO problem with composite
        pass
    # print('list_of_nested_ns_id: {}'.format(list_of_nested_ns_id))
    nsd_response = descriptor['nsd:nsd-catalog']['nsd-composite'][0]
    # create a nx.Graph
    g = nx.Graph()
    # dealing with the 'constituent-nsd'
    nsd_array = nsd_response['constituent-nsd']
    # for each constituent-nsd of composite remapping of vl names (if necessary) and create the graph
    for nsd_nested_item in nsd_array:
        # print(nsd_nested_item)
        ns_ir_net_map = nsir_db.get_network_mapping(ns_id)
        ns_ir_rename_map = nsir_db.get_renaming_network_mapping(ns_id)
        # print(ns_ir_net_map, ns_ir_rename_map)
        # network remapping part
        mapping = {}
        if bool(ns_ir_net_map):
            # case of composite NOT from scratch
            if bool(ns_ir_rename_map):
                for vl in ns_ir_net_map['nestedVirtualLinkConnectivity'][nsd_nested_item['nested-nsd-id']]:
                    for key_vl, value_vl in vl.items():
                        for key_rename, value_rename in ns_ir_rename_map.items():
                            if value_vl == value_rename:
                                mapping[key_vl] = key_rename
            # case of composite from scratch
            else:
                for vl in ns_ir_net_map['nestedVirtualLinkConnectivity'][nsd_nested_item['nested-nsd-id']]:
                    for key_vl, value_vl in vl.items():
                        mapping[key_vl] = value_vl
        else:
            print("TODO")  # TODO
            pass
        # print('Network mapping {}:'.format(mapping))
        nsd_json = nsd_db.get_nsd_json(nsd_nested_item['nested-nsd-id'])
        domain_federation = next(item['federated_domain'] for item in list_of_nested_ns_id if item.get("nsd_id") == nsd_nested_item['nested-nsd-id'])
        if isinstance(domain_federation, dict):
            domain_federation = next(iter(domain_federation))
        # print("Federated domain: {}".format(domain_federation))
        # find df and instantiation level of composite nsd
        level = "{}_{}_{}".format(nsd_nested_item['nested-nsd-id'],
                                  nsd_nested_item['nested-ns-df-id'],
                                  nsd_nested_item['nested-ns-inst-level-id'])
        ns_network = {}
        # retrieve the json of composite nsd (with correct df and instantiation level)
        list_osm_json, default_index = ifa014_conversion(nsd_json)
        for element in list_osm_json:
            if element['nsd:nsd-catalog']['nsd'][0]['id'] == level:
                ns_network = element

        # creating graph of nested NS
        nsd_response = ns_network['nsd:nsd-catalog']['nsd'][0]
        # renaming involved network
        for vld_item in nsd_response['vld']:
            vld_name = vld_item['name']
            if vld_item['name'] in mapping:
                vld_item['short-name'] = mapping[vld_name]
                vld_item['id'] = mapping[vld_name]
                vld_item['name'] = mapping[vld_name]
        # dealing with the 'constituent-vnfd'
        vnfd_array = nsd_response['constituent-vnfd']
        for nsd_item in vnfd_array:
            # current_node_id = g.number_of_nodes()
            current_node_id = selected_node(g, nsd_item['vnfd-id-ref'])
            # add a node in the nx.Graph for every vnfd
            g.add_node(current_node_id,
                       features="VNFD: {}".format(nsd_item['vnfd-id-ref']),
                       ref_node_id=nsd_item['member-vnf-index'],
                       name=nsd_item['vnfd-id-ref'],
                       type="VNFD",
                       shape="circle",
                       nested=[nsd_nested_item['nested-nsd-id']],
                       federation=[str(domain_federation)],
                       group=1)
        # dealing with the 'vld'
        vld_array = nsd_response['vld']
        for vld_item in vld_array:
            vld_connections_array = vld_item['vnfd-connection-point-ref']
            # current_node_id = g.number_of_nodes()
            current_node_id = selected_node(g, vld_item['name'])
            # add a node in the nx.Graph for every vld
            g.add_node(current_node_id,
                       features="VLD: {}".format(vld_item['name']),
                       name=vld_item['name'],
                       type="VLD",
                       shape="rect",
                       # nested=[nsd_nested_item['nested-nsd-id']],
                       # federation=str(domain_federation),
                       group=2)
            # nested parameters is a list of shared components
            if 'nested' in g.nodes[current_node_id]:
                g.nodes[current_node_id]['nested'].append(nsd_nested_item['nested-nsd-id'])
            else:
                g.nodes[current_node_id]['nested'] = [nsd_nested_item['nested-nsd-id']]
            # federation parameters is a list of shared components
            if 'federation' in g.nodes[current_node_id]:
                g.nodes[current_node_id]['federation'].append(str(domain_federation))
            else:
                g.nodes[current_node_id]['federation'] = [str(domain_federation)]
            list_ids = list()
            # dealing with the corresponding links between different elements
            for vld_connection_item in vld_connections_array:
                list_ids.append((vld_connection_item['member-vnf-index-ref'], vld_connection_item['vnfd-id-ref']))
            for element in list_ids:
                for nodes in g:
                    if g.nodes[nodes]['group'] == 1:
                        if element[0] == g.nodes[nodes]['ref_node_id'] and element[1] == g.nodes[nodes]['name']:
                            # add a link
                            g.add_edge(nodes, selected_node(g, vld_item['name']))
        # adding placement info
        id_for_placement = ''
        for nested_ns_id in list_of_nested_ns_id:
            if nested_ns_id['nsd_id'] == nsd_nested_item['nested-nsd-id']:
                id_for_placement = nested_ns_id['ns_id']
        if nsir_db.exists_nsir(id_for_placement):
            placement_info = nsir_db.get_placement_info(id_for_placement)
            # update the name of vl in common for composite for placement algorithm
            for used_vls in placement_info['usedVLs']:
                for i, mapped_vl in enumerate(used_vls['mappedVLs']):
                    if mapped_vl in mapping:
                        used_vls['mappedVLs'][i] = mapping[mapped_vl]

            if placement_info:
                g = add_placement(g, placement_info)
    # d = json_graph.node_link_data(g)  # node-link format to serialize
    # print(d)
    # return d
    return g


def json_network_composite_nsd(descriptor, placement_info=None):
    """
    Return the node-link format of the YAML NS Composite Descriptor
    :param descriptor: yaml object representing the NS composite descriptor
    :param placement_info: placement informartion to be represented (set to None)
    :return: nx json graph format
    """
    nsd_response = descriptor['nsd:nsd-catalog']['nsd-composite'][0]
    # create a nx.Graph
    g = nx.Graph()
    # dealing with the 'constituent-nsd'
    nsd_array = nsd_response['constituent-nsd']
    for nsd_item in nsd_array:
        current_node_id = g.number_of_nodes()
        # add a node in the nx.Graph for every vnfd
        g.add_node(current_node_id,
                   features="NSD: {}".format(nsd_item['nsd-id-ref']),
                   ref_node_id=nsd_item['member-ns-index'],
                   name=nsd_item['nsd-id-ref'],
                   type="NSD",
                   shape="circle",
                   group=1)
    # dealing with the 'vld'
    vld_array = nsd_response['vld']
    for vld_item in vld_array:
        vld_connections_array = vld_item['nsd-connection-point-ref']
        current_node_id = g.number_of_nodes()
        # add a node in the nx.Graph for every vld
        g.add_node(current_node_id,
                   features="VLD: {}".format(vld_item['name']),
                   name=vld_item['name'],
                   type="VLD",
                   shape="rect",
                   group=2)

        list_ids = list()
        # dealing with the corresponding links between different elements
        for vld_connection_item in vld_connections_array:
            list_ids.append((vld_connection_item['member-ns-index-ref'], vld_connection_item['nsd-id-ref']))
        for element in list_ids:
            for nodes in g:
                if g.nodes[nodes]['group'] == 1:
                    if element[0] == g.nodes[nodes]['ref_node_id'] and element[1] == g.nodes[nodes]['name']:
                        # add a link
                        g.add_edge(nodes, current_node_id)

    if placement_info:
        g = add_placement(g, placement_info)
    # d = json_graph.node_link_data(g)  # node-link format to serialize
    # print(d)
    # return d
    return g


def json_network_nsd(descriptor, placement_info=None):
    """
    Return the node-link format of the YAML NS Descriptor or NS Nested/Regular Instance
    :param descriptor: yaml object representing the NS descriptor
    :param placement_info: placement informartion to be represented (set to None)
    :return: nx json graph format
    """
    nsd_response = descriptor['nsd:nsd-catalog']['nsd'][0]
    # create a nx.Graph
    g = nx.Graph()
    # dealing with the 'constituent-vnfd'
    vnfd_array = nsd_response['constituent-vnfd']
    for nsd_item in vnfd_array:
        current_node_id = g.number_of_nodes()
        # add a node in the nx.Graph for every vnfd
        g.add_node(current_node_id,
                   features="VNFD: {}".format(nsd_item['vnfd-id-ref']),
                   ref_node_id=nsd_item['member-vnf-index'],
                   name=nsd_item['vnfd-id-ref'],
                   type="VNFD",
                   shape="circle",
                   group=1)
    # dealing with the 'vld'
    vld_array = nsd_response['vld']
    for vld_item in vld_array:
        vld_connections_array = vld_item['vnfd-connection-point-ref']
        current_node_id = g.number_of_nodes()
        # add a node in the nx.Graph for every vld
        g.add_node(current_node_id,
                   features="VLD: {}".format(vld_item['name']),
                   name=vld_item['name'],
                   type="VLD",
                   shape="rect",
                   group=2)

        list_ids = list()
        # dealing with the corresponding links between different elements
        for vld_connection_item in vld_connections_array:
            list_ids.append((vld_connection_item['member-vnf-index-ref'], vld_connection_item['vnfd-id-ref']))
        for element in list_ids:
            for nodes in g:
                if g.nodes[nodes]['group'] == 1:
                    if element[0] == g.nodes[nodes]['ref_node_id'] and element[1] == g.nodes[nodes]['name']:
                        # add a link
                        g.add_edge(nodes, current_node_id)

    if placement_info:
        g = add_placement(g, placement_info)
    # d = json_graph.node_link_data(g)  # node-link format to serialize
    # print(d)
    # return d
    return g


def json_network_vnfd(descriptor):
    """
    Return the node-link format of the YAML VNF Descriptor
    :param descriptor: yaml object representing the VNF descriptor
    :return: nx json graph format
    """
    vnfd_response = descriptor['vnfd:vnfd-catalog']['vnfd'][0]
    # create a nx.Graph
    g = nx.Graph()
    # dealing with the 'connection-point'
    for cp in vnfd_response['connection-point']:
        current_node_id = g.number_of_nodes()
        # add a node in the nx.Graph for every cp
        g.add_node(current_node_id,
                   features="Connection Point: {}\n{}".format(cp['name'], cp['type']),
                   name=cp['name'],
                   type="CP",
                   shape="circle",
                   group=1)
    # dealing with the 'internal-vld'
    if 'internal-vld' in vnfd_response:
        for internal_vld in vnfd_response['internal-vld']:
            current_node_id = g.number_of_nodes()
            # add a node in the nx.Graph for every internal vld
            g.add_node(current_node_id,
                       features="Internal VLD: {}\n{}".format(internal_vld['name'], internal_vld['type']),
                       name=internal_vld['name'],
                       type='INTERNAL VLD',
                       shape="circle",
                       internal_cp=[d['id-ref'] for d in internal_vld['internal-connection-point']],
                       group=3)
    # dealing with the 'vdu'
    for vdu in vnfd_response['vdu']:
        current_node_id = g.number_of_nodes()
        # add a node in the nx.Graph for every vdu
        g.add_node(current_node_id,
                   features="VDU: {}\n{}\n\tvcpu count: {}\n\tmemory mb: {}\n\tstorage gb: {}".
                   format(vdu['name'],
                          vdu['image'],
                          vdu['vm-flavor']['vcpu-count'],
                          vdu['vm-flavor']['memory-mb'],
                          vdu['vm-flavor']['storage-gb']),
                   name=vdu['name'],
                   type="VDU",
                   shape="circle",
                   group=2)
        # connecting different links
        for interface in vdu['interface']:
            if interface['type'] == 'EXTERNAL':
                for node in range(len(g.nodes)):
                    if g.nodes[node]['group'] == 1:
                        if interface['external-connection-point-ref'] == g.nodes[node]['name']:
                            g.add_edge(node, current_node_id)
            else:  # interface['type'] == 'INTERNAL'
                for node in range(len(g.nodes)):
                    if g.nodes[node]['group'] == 3:
                        if interface['internal-connection-point-ref'] in g.nodes[node]['internal_cp']:
                            g.add_edge(node, current_node_id)
    # d = json_graph.node_link_data(g)  # node-link format to serialize
    # print(d)
    # return d
    return g


def create_osm_files(osm_json, directory):
    """
    Create the tar.gz file containing the YAML descriptor (in OSM format) to be onboarded on configured OSM
    :param osm_json: json representing the nsd/vnfd descriptor in OSM format
    :param directory: directory where tar.gz file is created
    :return: yaml_filename, yaml_root: name of tar.gz file (with corresponding path) and directory
    """
    if 'vnfd:vnfd-catalog' in osm_json:
        name_osm_descriptor = osm_json['vnfd:vnfd-catalog']['vnfd'][0]['name']
        # in order to osm to upload this package
        name_osm_descriptor = name_osm_descriptor + '_vnfd'
    else:
        name_osm_descriptor = osm_json['nsd:nsd-catalog']['nsd'][0]['name']
        # in order to osm to upload this package
        name_osm_descriptor = name_osm_descriptor + '_nsd'
    yaml_root = os.path.join(directory, name_osm_descriptor)
    # create the directory of yaml
    if os.path.exists(yaml_root):
        log_queue.put(["INFO", " '{}' directory existing. Going to erase it.".format(yaml_root)])
        shutil.rmtree(yaml_root)
    os.makedirs(yaml_root)
    with open(os.path.join(yaml_root, "{}.yaml".format(name_osm_descriptor)), 'w') as ex:
        yaml.dump(osm_json, ex, default_flow_style=False)
    # set the type of Descriptor (NSD, VNFD or not valid)
    # create the 'icons' sub-directory (no logo inserted so far)
    os.makedirs(os.path.join(yaml_root, 'icons'))
    # # create a tar.gz of the yaml (and related folder))
    yaml_filename = yaml_root + '.tar.gz'
    if os.path.exists(yaml_filename):
        log_queue.put(["INFO", " '{}' directory existing. Going to erase it.".format(yaml_root)])
        os.remove(yaml_filename)
    with tarfile.open(yaml_filename, "w:gz") as tar:
        tar.add(yaml_root, arcname=os.path.basename(yaml_root))
    return yaml_filename, yaml_root
