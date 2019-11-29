# Copyright 2018 CTTC www.cttc.es
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
File description
"""

# python imports
import json
import re
from http.client import HTTPConnection
from six.moves.configparser import RawConfigParser
from uuid import uuid4
from json import dumps, loads, load
import itertools
import sys
import netaddr
import copy

# project imports
from coreMano.cloudifyWrapper import CloudifyWrapper
from coreMano.osmWrapper import OsmWrapper
# from sm.rooe.pa import pa
from db.ns_db import ns_db
from db.operation_db import operation_db
from db.nsir_db import nsir_db
from db.resources_db import resources_db
from coreMano.coreManoWrapper import createWrapper
from sm.eenet import eenet
from nbi import log_queue
from sbi import sbi

config = RawConfigParser()
config.read("../../coreMano/coreMano.properties")
core_mano_name = config.get("CoreMano", "name")

def amending_pa_output(nsd_info, placement_info):
    """
    Function description
    Parameters
    ----------
    nsd_info: dict
        dictionary with information of the nsd and the vnfs included in it.
    placement_info:
        dictionary with the output of the PA, but requires amendments to include VL that are not connecting VNF's
    -------
    Returns
    ---------
    dict
        Dictionary with the placement_info containing all virtual links, including the ones that are not connecting VNFs.
    """
    list_of_vnfs = []
    for elem in nsd_info['VNFs']:
        list_of_vnfs.append(elem['VNFid'])
    for elem in placement_info['usedNFVIPops']:

        new_mappedvnfs =[] 
        for vnf in elem['mappedVNFs']:
            # log_queue.put(["DEBUG", "la vnf que miro es: %s"%vnf])
            if vnf in list_of_vnfs:
                new_mappedvnfs.append(vnf)
        elem['mappedVNFs'] = new_mappedvnfs

    VNF_links_in_nsd = {}
    VNF_links_in_pa_output = []
    for vl in nsd_info["VNFLinks"]:
        VNF_links_in_nsd[vl["VLid"]] = vl['source'] 
        VNF_links_in_nsd[vl["id"]] = vl['source']
        #if the vl is not connecting vnf's, the vl will have destination field set to None
    for elem in placement_info.keys():
        if (elem == 'usedVLs' or elem == 'usedLLs') : 
            if placement_info[elem]:
                # the list is not empty
                for pop in placement_info[elem]:
                    for vl in pop["mappedVLs"]:
                        VNF_links_in_pa_output.append(vl)
    pop_id = None
    for vl in VNF_links_in_nsd.keys():
        if vl not in VNF_links_in_pa_output:
            # we are missing this link, we have to look for the associated vnf, check where it is
            # and then update the mappedVLs field of used VLs
            for pop in placement_info['usedNFVIPops']:
               if VNF_links_in_nsd[vl] in pop['mappedVNFs']:
                   pop_id = pop["NFVIPoPID"]
                   # we have found our element
                   present = False
                   for vl_p in placement_info['usedVLs']:
                       if 'NFVIPoPID' in vl_p.keys(): #R1
                           if vl_p["NFVIPoPID"] == pop_id:
                               present = True
                               vl_p['mappedVLs'].append(vl)
                       else: #R2
                           if vl_p["NFVIPoP"] == pop_id:
                               present = True
                               vl_p['mappedVLs'].append(vl)

                   if not present:
                       #the vl is not mapped anywhere and we need to create an entry for this in the usedVLs
                       placement_info['usedVLs'].append({'NFVIPoP': pop_id, 'mappedVLs': [vl]})
    return placement_info

def extract_nsd_info_for_pa(nsd_json, vnfds_json, body):
    """
    Function description
    Parameters
    ----------
    nsd_vnfd: dict
        dictionary with information of the nsd and the vnfs included in it.
    request:
        dictionary with the information received in the NBI which has the format:
        {"flavour_id": "flavour1",
         "ns_instantiation_level_id": "nsInstantiationLevel1}
    -------
    dict
        Dictionary with the information that is relevant for the deployment of the service.
    """
    nsd = {"nsd": {"id": "", "name": "", "VNFs": [], "VNFLinks": [],
                   "max_latency": 0, "target_availability": 0, "max_cost": 0}}
    VLs = {}
    max_latency = 10000.0

    NSD = nsd_json
    vnfds = vnfds_json

    flavourId = body.flavour_id
    nsLevelId = body.ns_instantiation_level_id

    ID = NSD["nsd"]["nsdIdentifier"]
    name = NSD["nsd"]["nsdName"]
    nsd["nsd"]["id"] = str(ID)
    nsd["nsd"]["name"] = str(name)
    Df_descript = None
    nsDf = NSD["nsd"]["nsDf"]
    vl_prof_desc = {} # (virtualLinkProfileId, virtualLinkDescId)
    for df in nsDf:
        if df["nsDfId"] == flavourId:
            Df_descript = df
            for instlevel in df["nsInstantiationLevel"]:
                if instlevel["nsLevelId"] == nsLevelId:
                    vnfToLevelMapping = instlevel["vnfToLevelMapping"]
                    virtualLinkToLevelMapping = instlevel["virtualLinkToLevelMapping"]
            for vl_profile in df['virtualLinkProfile']:
                vl_prof_desc[vl_profile['virtualLinkProfileId']] =\
                    vl_profile['virtualLinkDescId']
    vnfs_il = []  # storing the name of the vnfs in the requested instantiation level
    if Df_descript is not None:
        vnfCps = {} # CPs of the VNFs
        for vnfelem in vnfToLevelMapping:
            vnf = vnfelem["vnfProfileId"]
            numberOfInstances = vnfelem["numberOfInstances"]
            for profile in Df_descript["vnfProfile"]:
                if (vnf == profile["vnfProfileId"]):
                    vnfdId = profile["vnfdId"]
                    vnfdDf = profile["flavourId"]
                    vnfs_il.append(vnfdId)

                    # Get a list of CP.{id,vl_id} for the VNFs
                    # CPs needed by the R2 API
                    for cpConnectivity in profile['nsVirtualLinkConnectivity']:
                        if vnfdId not in vnfCps:
                            vnfCps[vnfdId] = []
                        for cp_id in cpConnectivity['cpdId']:
                            vnfCps[vnfdId] += [{
                                'cpId': cp_id,
                                'vl_id': vl_prof_desc[cpConnectivity['virtualLinkProfileId']]
                            }]


                    for vId in vnfds.keys():
                        # log_queue.put(["DEBUG", "the value of vId is: %s"%(vId)])
                        if (vId == vnfdId):
                            for df in vnfds[vId]["deploymentFlavour"]:
                                if (df["flavourId"] == vnfdDf):
                                    vnfdvdu = df["vduProfile"][0]["vduId"]
                            for vdu in vnfds[vId]["vdu"]:
                                if (vdu["vduId"] == vnfdvdu):
                                    virtualComputeDesc = vdu["virtualComputeDesc"]
                                    virtualStorageDesc = vdu["virtualStorageDesc"][0]
                            for elem in vnfds[vId]["virtualComputeDesc"]:
                                if (elem["virtualComputeDescId"] == virtualComputeDesc):
                                    memory = elem["virtualMemory"]["virtualMemSize"]
                                    cpu = elem["virtualCpu"]["numVirtualCpu"]

                                    # We assume that a "mec" flag is present in the
                                    # virtualComputeDesc element.
                                    # This is really tentative, just for checking.
                                    # To be removed if/when the NSD will include
                                    # AppD references
                                    mec = False
                                    if "mec" in elem:
                                      mec = elem["mec"]

                            for elem in vnfds[vId]["virtualStorageDesc"]:
                                if (elem["id"] == virtualStorageDesc):
                                    storage = elem["sizeOfStorage"]
                            nsd["nsd"]["VNFs"].append({"VNFid": str(vnfdId), "instances": numberOfInstances,
                                                       "location": {"center": {"longitude": 0,
                                                                               "latitude": 0},
                                                                    "radius": 10},
                                                       "requirements": {"cpu": cpu,
                                                                        "ram": memory,
                                                                        "storage": storage,
                                                                        "mec": mec},
                                                       "failure_rate": 0,
                                                       "processing_latency": 0})
        # be careful, this function assumes that there is not vnffg and then, it generates "artificial links",
        # otherwise, we have to proceed in a different way. It is handling the case where a VNF is connected to
        # a vld but not connected to another VNF
        vld_to_vnf = {}
        for vnflink in virtualLinkToLevelMapping:
            for profile in Df_descript["vnfProfile"]:
                if (profile["vnfdId"] in vnfs_il):
                    for link in profile["nsVirtualLinkConnectivity"]:
                        if (link["virtualLinkProfileId"] == vnflink["virtualLinkProfileId"]):
                            if not vnflink["virtualLinkProfileId"] in vld_to_vnf:
                                vld_to_vnf[vnflink["virtualLinkProfileId"]] = {}
                                vld_to_vnf[vnflink["virtualLinkProfileId"]
                                           ]["bw"] = vnflink["bitRateRequirements"]["root"]
                                vld_to_vnf[vnflink["virtualLinkProfileId"]]["vnfs"] = []
                            vld_to_vnf[vnflink["virtualLinkProfileId"]]["vnfs"].append(profile["vnfdId"])

        vld_to_vnf2 = {}
        for vld in vld_to_vnf.keys():
            for vlprofile in Df_descript["virtualLinkProfile"]:
                if (vlprofile["virtualLinkProfileId"] == vld):
                    if not vlprofile["virtualLinkDescId"] in vld_to_vnf2:
                        vld_to_vnf2[vlprofile["virtualLinkDescId"]] = {}
                    vld_to_vnf2[vlprofile["virtualLinkDescId"]]["vnfs"] = vld_to_vnf[vld]["vnfs"]
                    vld_to_vnf2[vlprofile["virtualLinkDescId"]]["bw"] = vld_to_vnf[vld]["bw"]
                    vl_flavour = vlprofile["flavourId"]
                    for linkdesc in NSD["nsd"]["virtualLinkDesc"]:
                        if (linkdesc["virtualLinkDescId"] == vlprofile["virtualLinkDescId"]):
                            for df in linkdesc["virtualLinkDf"]:
                                if (df["flavourId"] == vl_flavour):
                                    vld_to_vnf2[vlprofile["virtualLinkDescId"]]["latency"] = df["qos"]["latency"]


        # Replace CPs VL ids by the VNFLink
        for vld in vld_to_vnf2.keys():
            for vnf in vnfCps.keys():
                for i in range(len(vnfCps[vnf])):
                    if vnfCps[vnf][i]['vl_id'] == vld:
                        vnfCps[vnf][i]['VNFLink'] = {
                            'id': vld,
                            'latency': vld_to_vnf2[vld]['latency'],
                            'traversal_probability': 1,
                            'required_capacity': float(vld_to_vnf2[vld]["bw"])
                        }

                # Include the information in the resulting VNF
                for i in range(len(nsd['nsd']['VNFs'])):
                    if nsd['nsd']['VNFs'][i]['VNFid'] == vnf:
                        nsd['nsd']['VNFs'][i]['CP'] = vnfCps[vnf]


        for vld in vld_to_vnf2.keys():
            if (len(vld_to_vnf2[vld]['vnfs']) > 1):
                endpoints = list(itertools.combinations(vld_to_vnf2[vld]['vnfs'], 2))
                log_queue.put(["INFO", dumps(endpoints, indent=4)])
                for pair in endpoints:
                    nsd["nsd"]["VNFLinks"].append({"source": str(pair[0]), "destination": str(pair[1]),
                                                   "required_capacity": float(vld_to_vnf2[vld]["bw"]),
                                                   "required_latency": vld_to_vnf2[vld]["latency"],
                                                   #PA_testing
                                                   "latency": vld_to_vnf2[vld]["latency"],
                                                   "VLid": vld,
                                                   #PA_testing
                                                   "id": vld,
                                                   "traversal_probability": 1})
            elif (len(vld_to_vnf2[vld]['vnfs']) == 1):
                nsd["nsd"]["VNFLinks"].append({"source": vld_to_vnf2[vld]['vnfs'][0], "destination": "None",
                                               "required_capacity": float(vld_to_vnf2[vld]["bw"]),
                                               "required_latency": vld_to_vnf2[vld]["latency"],
                                               #PA_testing
                                               "latency": vld_to_vnf2[vld]["latency"],
                                               "VLid": vld,
                                               #PA_testing
                                               "id": vld,
                                               "traversal_probability": 1})

        # Include the SAPs
        nsd['nsd']['SAP'] = []
        for sapd in NSD['nsd']['sapd']:
            nsd['nsd']['SAP'] += [{
                'CPid': sapd['associatedCpdId']
            } if 'associatedCpdId' in sapd else {
                'VNFLink': sapd['nsVirtualLinkDescId']
            }]

            # Seek possible location constraint
            if body.sap_data:
                for sap_data in body.sap_data:
                    if sap_data.sapd_id == sapd['cpdId'] and isinstance(sap_data.location_info,dict):
                        nsd['nsd']['SAP'][-1]['location']['center']['longitude'] = sap_data.location_info.longitude
                        nsd['nsd']['SAP'][-1]['location']['center']['latitude'] = sap_data.location_info.latitude
                        nsd['nsd']['SAP'][-1]['location']['radius'] = sap_data.location_info.range



        nsd["nsd"]["max_latency"] = max_latency
        nsd["nsd"]["target_availability"] = 0.0
        nsd["nsd"]["max_cost"] = 1000000000
    return nsd


def parse_resources_for_pa(resources, vnfs_ids):
    """
    Converts the resources obtained from MTP to the format expected by PA.
    Parameters
    ----------
    resources: json
        resources obtained from MTP
    Returns
    -------
        resources json in PA format
    """
    pa_resources = {"resource_types": ["cpu", "memory", "storage"],
                    "NFVIPoPs": [],
                    "LLs": [],
                    "VNFCosts": [],
                    "LLCosts": [],
                    "VLCosts": []
                    }

    gw_pop_mapping = {}  # for easier parsing save nfvipops gateways

    for pop in resources["NfviPops"]:
        pa_pop = {}
        pa_pop["id"] = pop["nfviPopAttributes"]["vimId"]
        # only 1 gw by PoP for now?
        pa_pop["gw_ip_address"] = pop["nfviPopAttributes"]["networkConnectivityEndpoint"][0]["netGwIpAddress"]
        pa_pop["capabilities"] = {}
        pa_pop["availableCapabilities"] = {}

        # MEC capabilities: Assumes that the MTP adds a MEC flag according
        # to the current version of the MTP API.
        pa_pop["capabilities"]["mec"] = False
        pa_pop["availableCapabilities"]["mec"] = False
        if "MecCapable" in pop["nfviPopAttributes"]:
          if str(pop["nfviPopAttributes"]["MecCapable"]).lower() == "true" or pop["nfviPopAttributes"]["MecCapable"] == True:
            pa_pop["capabilities"]["mec"] = True
            pa_pop["availableCapabilities"]["mec"] = True

        pa_pop["capabilities"]["cpu"] = int(pop["nfviPopAttributes"]["resourceZoneAttributes"][0]["cpuResourceAttributes"]["totalCapacity"])
        pa_pop["availableCapabilities"]["cpu"] = int(pop["nfviPopAttributes"]["resourceZoneAttributes"][0]["cpuResourceAttributes"]["availableCapacity"])
        pa_pop["capabilities"]["ram"] = int(pop["nfviPopAttributes"]["resourceZoneAttributes"][0]["memoryResourceAttributes"]["totalCapacity"])
        pa_pop["availableCapabilities"]["ram"] = int(pop["nfviPopAttributes"]["resourceZoneAttributes"][0]["memoryResourceAttributes"]["availableCapacity"])
        pa_pop["capabilities"]["storage"] = int(pop["nfviPopAttributes"]["resourceZoneAttributes"][0]["storageResourceAttributes"]["totalCapacity"])
        pa_pop["availableCapabilities"]["storage"] = int(pop["nfviPopAttributes"]["resourceZoneAttributes"][0]["storageResourceAttributes"]["availableCapacity"])
        # pa_pop["capabilities"]["storage"] = 1000
        # pa_pop["availableCapabilities"]["storage"] = 1000
        pa_pop["capabilities"]["bandwidth"] = 0
        pa_pop["availableCapabilities"]["bandwidth"] = 0
        pa_pop["internal_latency"] = 0
        pa_pop["failure_rate"] = 0
       # Store NFVI PoP location if present as coordinates
        center = None
        coord_regex = '(\-?\d+(\.\d+)?),\s*(\-?\d+(\.\d+)?)'
        search = re.search(coord_regex,
                    pop["nfviPopAttributes"]['geographicalLocationInfo'])
        if search:
            pa_pop["location"] = {
                'radius': 0,
                'center': {
                    "latitude": float(search.group(1)),
                    "longitude": float(search.group(3))
                }
            }
        else: 
            pa_pop["location"] = {"radius": 0, "center": {"latitude": 0, "longitude": 0}}
        gw_pop_mapping[pa_pop["gw_ip_address"]] = pa_pop["id"]
        pa_resources["NFVIPoPs"].append(pa_pop)
        vl_cost = {}
        vl_cost["NFVIPoP"] = pop["nfviPopAttributes"]["vimId"]
        vl_cost["cost"] = 0
        pa_resources["VLCosts"].append(vl_cost)
        for vnf in vnfs_ids:
            vnf_cost = {}
            vnf_cost["vnfid"] = vnf
            vnf_cost["NFVIPoPid"] = pop["nfviPopAttributes"]["vimId"]
            vnf_cost["cost"] = 0
            pa_resources["VNFCosts"].append(vnf_cost)

    for ll in resources["logicalLinkInterNfviPops"]:
        pa_ll = {}
        pa_ll["LLid"] = ll["logicalLinks"]["logicalLinkId"]
        pa_ll["delay"] = ll["logicalLinks"]["networkQoS"]["linkDelayValue"]
        pa_ll["length"] = 0
        pa_ll["capacity"] = {}
        pa_ll["capacity"]["total"] = ll["logicalLinks"]["totalBandwidth"]
        pa_ll["capacity"]["available"] = ll["logicalLinks"]["availableBandwidth"]
        pa_ll["source"] = {}
        pa_ll["source"]["GwIpAddress"] = ll["logicalLinks"]["srcGwIpAddress"]
        pa_ll["source"]["id"] = gw_pop_mapping[pa_ll["source"]["GwIpAddress"]]
        pa_ll["destination"] = {}
        pa_ll["destination"]["GwIpAddress"] = ll["logicalLinks"]["dstGwIpAddress"]
        pa_ll["destination"]["id"] = gw_pop_mapping[pa_ll["destination"]["GwIpAddress"]]
        pa_resources["LLs"].append(pa_ll)
        ll_cost = {}
        ll_cost["LL"] = ll["logicalLinks"]["logicalLinkId"]
        ll_cost["cost"] = ll["logicalLinks"]["networkQoS"]["linkCostValue"]
        pa_resources["LLCosts"].append(ll_cost)

    log_queue.put(["DEBUG", "Resources for PA are:"])
    log_queue.put(["DEBUG", dumps(pa_resources, indent=4)])

    return pa_resources

def extract_vls_info_mtp(resources, extracted_info, placement_info, nsId, nestedInfo=None):
    """
    Function description
    Parameters
    ----------
    nsId: string
        param1 description
    nsd_json: json
    vnfds_json: dict {vnfdId: vnfd_json,...}
    body: json
        {"flavour_id": string, "nsInstantiationLevelId": string}

    Returns
    -------
    name: type
        return description
    """
    # vls_info will be a list of LL to be deployed where each LL is a json
    # according the input body that the mtp expects.
    vls_info = {"interNfviPopNetworkType": "L2-VPN",
                "networkLayer": "VLAN",
                "logicalLinkPathList": [],
                "metaData": []
               }
    # for each LL in the placement info, get its properties and append it to the vls_info list
    network_info = nsir_db.get_vim_networks_info(nsId)
    vnf_info = nsir_db.get_vnf_deployed_info(nsId)
    # first parse the resources information to have a more usable data structure of LL info
    ll_resources = {}
    for ll in resources["logicalLinkInterNfviPops"]:
        llId = ll["logicalLinks"]["logicalLinkId"]
        ll_resources[llId] = {}
        ll_resources[llId]["interNfviPopNetworkType"] = ll["logicalLinks"]["interNfviPopNetworkType"]
        ll_resources[llId]["dstGwIpAddress"] = ll["logicalLinks"]["dstGwIpAddress"]
        ll_resources[llId]["srcGwIpAddress"] = ll["logicalLinks"]["srcGwIpAddress"]
        ll_resources[llId]["localLinkId"] = ll["logicalLinks"]["localLinkId"]
        ll_resources[llId]["remoteLinkId"] = ll["logicalLinks"]["remoteLinkId"]
        ll_resources[llId]["networkLayer"] = ll["logicalLinks"]["networkLayer"]
        ll_resources[llId]["capacity"] = ll["logicalLinks"]["availableBandwidth"]
        ll_resources[llId]["latency"] = ll["logicalLinks"]["networkQoS"]["linkDelayValue"]
    # parse the extracted info to have a more usable data structure of VLs info

    vls_properties = {}
    for vl in extracted_info["nsd"]["VNFLinks"]:
        vlId = vl["VLid"]
        vls_properties[vlId] = {}
        vls_properties[vlId]["reqBandwidth"] = vl["required_capacity"]
        vls_properties[vlId]["reqLatency"] = vl["required_latency"]

    ll_processed = {}

    src_dst_link_triplet = []
    for ll in placement_info["usedLLs"]:
        llId = ll["LLID"]
        for vl in ll["mappedVLs"]:  # vl is the VL Id
            if not vl in ll_processed:
                ll_processed[vl] = 1
            else:
                ll_processed[vl] = ll_processed[vl] + 1
            ll_info = { "logicalLinkAttributes": {
                            "dstGwIpAddress": "",
                            "localLinkId": 0,
                            "logicalLinkId": "",
                            "remoteLinkId": 0,
                            "srcGwIpAddress": ""
                            },
                        "reqBandwidth": 0, #the following three elements, changed
                        "reqLatency": 0,
                        "metaData": []
                       }
            metadata, src_dst_link_triplet =  getVnfIPs(vl, extracted_info["nsd"]["VNFLinks"], vnf_info, network_info, \
                                              ll_processed[vl], placement_info, llId, resources, src_dst_link_triplet, nestedInfo)
            ll_info["metaData"] = metadata
            ll_info["reqBandwidth"] = ll_resources[llId]["capacity"]
            ll_info["reqLatency"] = ll_resources[llId]["latency"]
            ll_info["logicalLinkAttributes"]["dstGwIpAddress"] = ll_resources[llId]["dstGwIpAddress"]
            ll_info["logicalLinkAttributes"]["srcGwIpAddress"] = ll_resources[llId]["srcGwIpAddress"]
            ll_info["logicalLinkAttributes"]["remoteLinkId"] = ll_resources[llId]["remoteLinkId"]
            ll_info["logicalLinkAttributes"]["localLinkId"] = ll_resources[llId]["localLinkId"]
            ll_info["logicalLinkAttributes"]["logicalLinkId"] = llId
            vls_info["logicalLinkPathList"].append(ll_info)

    log_queue.put(["INFO", "VLS_info for eenet is:"])
    log_queue.put(["INFO", dumps(vls_info, indent=4)])

    return vls_info



def getVnfIPs(vlId, VNFLinks, vnf_info, network_info, index, placement_info, llId, resources, src_dst_link_triplet, nestedInfo=None):
    ll_type_llid_processed = 0
    for vl_link in VNFLinks:
        if (vl_link["VLid"] == vlId):
            # I should check also if VNFs are mapped in different PoPs and that we are in the correct logical link
            src = vl_link["source"]
            dst = vl_link["destination"]
            src_pop = None
            dst_pop = None
            for pop in placement_info["usedNFVIPops"]:
                if (src in pop["mappedVNFs"]):
                    src_pop = pop["NFVIPoPID"]
                if (dst in pop["mappedVNFs"]):
                    dst_pop = pop["NFVIPoPID"]
            triplet = [src,dst,vlId,llId]
            # if (src_pop != dst_pop and src_pop != None and dst_pop !=None):
            if (src_pop != dst_pop and src_pop != None and dst_pop !=None and (triplet not in src_dst_link_triplet) \
                and checkPoPsvsLlId (src_pop, dst_pop, llId, resources)):                      
                    src_dst_link_triplet.append(triplet)
                    # verify that the pops are really connected by the llId? It is needed to ensure that you are addressing
                    # the proper VNF Link (imagine you have the NS distributed in more than 2 NFVIPoPs)
                    vl = vl_link["VLid"]
                    src_vnf = vl_link["source"]
                    dst_vnf = vl_link["destination"]
                    for net in network_info["cidr"]:
                        # for composition/federation when having a nested in multi-pop 
                        # and you are instantiating everything from scratch
                        if nestedInfo:
                        # look for the appropriate link and change the vl value
                            nested_id = next(iter(nestedInfo))
                            for virtual_link in nestedInfo[nested_id][0]:
                                for key in virtual_link.keys():
                                    if (key == vl):
                                        vl = virtual_link[key]                   
                        if (net.find(vl) !=-1):
                            cidr = network_info["cidr"][net]
                            log_queue.put(["INFO", "el cidr es: %s"%cidr])
                            network_name = net
                    for vnf in vnf_info:
                        if (vnf["name"] == src_vnf):
                            for port in vnf["port_info"]: 
                                if netaddr.IPAddress(port["ip_address"]) in netaddr.IPNetwork(cidr):
                                    srcVnfIpAddress_tmp = port["ip_address"]
                                    srcVnfMacAddress_tmp = port["mac_address"]

                        if (vnf["name"] == dst_vnf):
                            for port in vnf["port_info"]: 
                                if netaddr.IPAddress(port["ip_address"]) in netaddr.IPNetwork(cidr):
                                    dstVnfIpAddress_tmp = port["ip_address"]
                                    dstVnfMacAddress_tmp = port["mac_address"]
                    #now we have to take into account the sense of the of the link
                    orderedpops = checkSenseLL(llId, resources)
                    if (orderedpops[0] == src_pop and orderedpops[1] == dst_pop):
                        srcVnfIpAddress = srcVnfIpAddress_tmp
                        srcVnfMacAddress = srcVnfMacAddress_tmp
                        dstVnfIpAddress = dstVnfIpAddress_tmp
                        dstVnfMacAddress = dstVnfMacAddress_tmp
                    else:
                        srcVnfIpAddress = dstVnfIpAddress_tmp
                        srcVnfMacAddress = dstVnfMacAddress_tmp
                        dstVnfIpAddress = srcVnfIpAddress_tmp
                        dstVnfMacAddress = srcVnfMacAddress_tmp
                    return [ [{"key": "srcVnfIpAddress", "value": srcVnfIpAddress}, {"key": "dstVnfIpAddress", "value": dstVnfIpAddress}, 
                              {"key": "srcVnfMacAddress", "value": srcVnfMacAddress }, {"key": "dstVnfMacAddress", "value": dstVnfMacAddress}, 
                              {"key": "networkName", "value": network_name}], src_dst_link_triplet ]

def checkSenseLL(llId, resources):
    #function to verify the sense of the llId
    for ll in resources["logicalLinkInterNfviPops"]:
        if (ll["logicalLinks"]["logicalLinkId"] == llId):
            src_gw = ll["logicalLinks"]["srcGwIpAddress"]
            dst_gw = ll["logicalLinks"]["dstGwIpAddress"]
    for PoP in resources["NfviPops"]:
        for gw in PoP["nfviPopAttributes"]["networkConnectivityEndpoint"]:
            if (gw["netGwIpAddress"] == src_gw):
                src_pop = PoP["nfviPopAttributes"]["nfviPopId"]
            if (gw["netGwIpAddress"] == dst_gw):
                dst_pop = PoP["nfviPopAttributes"]["nfviPopId"] 
    return [src_pop, dst_pop]

def checkPoPsvsLlId (src_pop, dst_pop, llId, resources):
    # function to verify that the src, dst pops are in the pops that the llId
    # is connecting
    gw_resources = []
    valid_pop_combination = False
    for PoP in resources["NfviPops"]:
        if (PoP["nfviPopAttributes"]["nfviPopId"] == src_pop or PoP["nfviPopAttributes"]["nfviPopId"] == dst_pop):
            for gw in PoP["nfviPopAttributes"]["networkConnectivityEndpoint"]:
                gw_resources.append(gw["netGwIpAddress"])
    for ll in resources["logicalLinkInterNfviPops"]:
        if (ll["logicalLinks"]["logicalLinkId"] == llId):
            if ( ll["logicalLinks"]["srcGwIpAddress"] in gw_resources and ll["logicalLinks"]["dstGwIpAddress"] in gw_resources):
                valid_pop_combination = True
    return valid_pop_combination


def extract_target_il(request):
    if (request.scale_type == "SCALE_NS"):
        return request.scale_ns_data.scale_ns_to_level_data.ns_instantiation_level        

def update_vls_info_mtp(nsId, scale_ops):
    """
    This function updates (create/destroy) the virtual links according to the scaling operations
    Parameters
    ----------
    nsId: string
        Identifier of the nsId
    scale_ops: list of dictionaries
        List with the performed scaling operations, on which vnf and which type (scale_in or scale_out)
    Returns
    -------
    vls_info: list of dictionaries
        List with the dictionary of the lls that need to be established
    vls_to_remove: list of id
        list with the id's of the lls that need to be removed
    """
    vnf_info = nsir_db.get_vnf_deployed_info(nsId)
    ll_links = nsir_db.get_vls(nsId)
    vls_info = {"interNfviPopNetworkType": "L2-VPN",
                "networkLayer": "VLAN",
                "logicalLinkPathList": [],
                "metaData": []
               }
    vls_to_remove = []
    # the idea is to add or remove based on the scaleVnfType action of scale_op
    # scale_ops = [{'scaleVnfType': 'SCALE_OUT', 'vnfIndex': '3', 'vnfName': 'spr21'}]
    # first we treat scale_in operations
    # if it is scale_in, we have to detect in the ll_links that either the src or the dst address is not in the ll_link list
    for link in ll_links:
        for i in link:
            value = link[i]
            ips = []
            for elem in value["metaData"]:
                if (elem["key"].find("VnfIpAddress") != -1):
                    ips.append(elem["value"])
            # both ip's have to be present
            for vnf in vnf_info:
                for port in vnf["port_info"]:
                    if port['ip_address'] in ips:
                        removed_ip = ips.pop(ips.index(port['ip_address']))
            if (len(ips) > 0):
                vls_to_remove.append(i)
    scale_out_ops = []
    for op in scale_ops:
        if (op["scaleVnfType"] == "SCALE_OUT" and (op["vnfName"] not in scale_out_ops)):
            scale_out_ops.append(op["vnfName"])
    # second we treat scale_out operations
    # if it is scale_out, we have to generate a new vl
    # the strategy to follow is the next one, we get the IP
    vl_list_scaling = []
    for vnf in scale_out_ops:
        vnfs_ips = []
        vnfs_mac = {}
        for elem in vnf_info:
            if (elem['name'] == vnf):
                for port in elem["port_info"]:
                    vnfs_ips.append(port['ip_address'])
                    vnfs_mac[port['ip_address']] = port['mac_address']
        # now we have a vector with the ips of all ports of all vnfs with
        # a name correspoding to a SCALE_OUT operation
        for link in ll_links:
            for i in link:
                value = link[i]
                for elem in value["metaData"]:
                    if (elem["key"].find("srcVnfIpAddress") != -1):
                        if (elem["value"] in vnfs_ips):
                            ip = vnfs_ips.pop(vnfs_ips.index(elem["value"]))
                            for ips in range(0,len(vnfs_ips)):
                               if (netaddr.IPNetwork(vnfs_ips[ips] + '/24') == netaddr.IPNetwork(ip + '/24')):
                                   #it means we have to copy this element and change the corresponding value
                                   new_vl = copy.deepcopy(value)
                                   # print ("the new vl: ", new_vl)
                                   for key in range(0, len(new_vl["metaData"])):
                                       if (new_vl["metaData"][key]["key"] == "srcVnfIpAddress"):
                                           new_vl["metaData"][key]["value"] = vnfs_ips[ips] 
                                       if (new_vl["metaData"][key]["key"] == "srcVnfMacAddress"):
                                           new_vl["metaData"][key]["value"] = vnfs_mac[vnfs_ips[ips]]                                             
                                   vl_list_scaling.append(new_vl)
                    if (elem["key"].find("dstVnfIpAddress") != -1):
                        if (elem["value"] in vnfs_ips):
                            ip = vnfs_ips.pop(vnfs_ips.index(elem["value"]))
                            for ips in range(0, len(vnfs_ips)):
                               if (netaddr.IPNetwork(vnfs_ips[ips] + '/24') == netaddr.IPNetwork(ip + '/24')):
                                   #it means we have to copy this element and change the corresponding value
                                   new_vl = copy.deepcopy(value)
                                   for key in range(0, len(new_vl["metaData"])):
                                       if (new_vl["metaData"][key]["key"] == "dstVnfIpAddress"):
                                           new_vl["metaData"][key]["value"] = vnfs_ips[ips]
                                       if (new_vl["metaData"][key]["key"] == "dstVnfMacAddress"):
                                           new_vl["metaData"][key]["value"] = vnfs_mac[vnfs_ips[ips]]                                             
                                   vl_list_scaling.append(new_vl)
    vls_info["logicalLinkPathList"] = vl_list_scaling
    return [vls_info, vls_to_remove]

def onboard_nsd_mano(nsd_json):
    """
    This function creates an instance of the MANO wrapper to upload the descriptor in the database of the corresponding 
    MANO platform
    Parameters
    ----------
    nsd_json: dict
        IFA014 network service descriptor.
    Returns
    -------
    """
    coreMano = createWrapper()
    if isinstance(coreMano, OsmWrapper): 
        coreMano.onboard_nsd(nsd_json)

def onboard_vnfd_mano(vnfd_json):
    """
    This function creates an instance of the MANO wrapper to upload the descriptor in the database of the corresponding 
    MANO platform
    Parameters
    ----------
    vnfd_json: dict
        IFA011 virtual network function descriptor.
    Returns
    -------
    """
    coreMano = createWrapper()
    if isinstance(coreMano, OsmWrapper): 
        coreMano.onboard_vnfd(vnfd_json)


def instantiate_ns(nsId, nsd_json, vnfds_json, request, nestedInfo=None):
    """
    Function description
    Parameters
    ----------
    param1: type
        param1 description
    Returns
    -------
    name: type
        return description
    """
    # extract the relevant information for the PA algorithm from the nsd_vnfd
    log_queue.put(["INFO", "*****Time measure: ROE starting ROE processing"])
    extracted_info = extract_nsd_info_for_pa(nsd_json, vnfds_json, request)
    log_queue.put(["INFO", "*****Time measure: ROE extracted NSD info at ROE"])
    log_queue.put(["INFO", dumps(extracted_info, indent=4)])
    # first get mtp resources and lock db
    resources = sbi.get_mtp_resources()
    log_queue.put(["INFO", "MTP resources are:"])
    log_queue.put(["INFO", dumps(resources, indent=4)])
    log_queue.put(["INFO", "*****Time measure: ROE retrieved MTP resources"])
    
    # ask pa to calculate the placement - read pa config from properties file
    config = RawConfigParser()
    config.read("../../sm/rooe/rooe.properties")
    pa_ip = config.get("PA", "pa.ip")
    pa_port = config.get("PA", "pa.port")
    pa_path = config.get("PA", "pa.path")
    pa_enable = config.get("PA", "pa.enable")
    placement_info = {}
    if pa_enable == "yes":
        pa_uri = "http://" + pa_ip + ":" + pa_port + pa_path
        # ask pa to calculate the placement - prepare the body
        paId = str(uuid4())
        pa_resources = parse_resources_for_pa(resources, vnfds_json.keys())
        body_pa = {"ReqId": paId,
                   "nfvi": pa_resources,
                   "nsd": extracted_info["nsd"],
                   "callback": "http://localhost:8080/5gt/so/v1/__callbacks/pa/" + paId}
        log_queue.put(["INFO", "Body for PA is:"])
        log_queue.put(["INFO", dumps(body_pa, indent=4)])
        # ask pa to calculate the placement - do request
        header = {'Content-Type': 'application/json',
                  'Accept': 'application/json'}
        log_queue.put(["INFO", "*****Time measure: ROE PA request generated"])
        try:
            conn = HTTPConnection(pa_ip, pa_port)
            conn.request("POST", pa_uri, dumps(body_pa), header)
            # ask pa to calculate the placement - read response and close connection
            rsp = conn.getresponse()
            placement_info = rsp.read().decode('utf-8')
            placement_info = loads(placement_info)
            conn.close()
        except ConnectionRefusedError:
            # the PA server is not running or the connection configuration is wrong
            log_queue.put(["ERROR", "the PA server is not running or the connection configuration is wrong"])
        log_queue.put(["INFO", "output of the PA is: "])
        log_queue.put(["INFO", placement_info])
        placement_info = amending_pa_output(extracted_info["nsd"], placement_info)
        log_queue.put(["INFO", "*****Time measure: ROE PA calculation done"])
        log_queue.put(["INFO", "PA tuned output is:"])
        log_queue.put(["INFO", placement_info])
    else:
        # to be removed when PA code tested: static placement for testing purposes
        pa_responses = config.items("RESPONSE")
        for pa_response in pa_responses:
            if (nsd_json["nsd"]["nsdIdentifier"].lower().find(pa_response[0]) !=-1):
                placement_info = json.loads(pa_response[1])
        log_queue.put(["INFO", "PA TUNED (manually) output is:"])
        log_queue.put(["DEBUG", placement_info])

    log_queue.put(["DEBUG", "Service NameId is: %s" % nsd_json["nsd"]["nsdIdentifier"]])
    if nestedInfo:
        key = next(iter(nestedInfo))
        log_queue.put(["DEBUG", "the key of nestedInfo in ROOE is: %s"%key])
        if len(nestedInfo[key]) > 1:
            # nested from a consumer domain
            nsId_tmp = nsId
        else:
            # nested local
            nsId_tmp = nsId + '_' + next(iter(nestedInfo))
    else:
        nsId_tmp = nsId

    nsir_db.save_placement_info(nsId_tmp, placement_info)
    # ask cloudify/OSM to deploy vnfs
    coreMano = createWrapper()
    deployed_vnfs_info = {}
    deployed_vnfs_info = coreMano.instantiate_ns(nsId, nsd_json, vnfds_json, request, placement_info, resources, nestedInfo)
    log_queue.put(["INFO", "The deployed_vnfs_info"])
    log_queue.put(["INFO", dumps(deployed_vnfs_info, indent=4)])
    if (deployed_vnfs_info is not None) and ("sapInfo" in deployed_vnfs_info):
        log_queue.put(["INFO", "ROOE: updating nsi:%s sapInfo: %s" % (nsId, deployed_vnfs_info["sapInfo"])])
        ns_db.save_sap_info(nsId, deployed_vnfs_info["sapInfo"])
        log_queue.put(["INFO", "*****Time measure: ROE created VNF's"])
    if deployed_vnfs_info is not None:
      # list of VLs to be deployed
      vls_info = extract_vls_info_mtp(resources, extracted_info, placement_info, nsId_tmp, nestedInfo)
      log_queue.put(["INFO", "*****Time measure: ROE extracted VL's at MTP"])
      # ask network execution engine to deploy the virtual links
      eenet.deploy_vls(vls_info, nsId_tmp)
    log_queue.put(["INFO", "*****Time measure: ROE created LL's at MTP"])

    # set operation status as SUCCESSFULLY_DONE
    if (nsId_tmp.find('_') == -1):
        # the service is single, I can update the operationId, and the status
        operationId = operation_db.get_operationId(nsId, "INSTANTIATION")
        if deployed_vnfs_info is not None:
            log_queue.put(["INFO", "NS Instantiation finished correctly"])
            operation_db.set_operation_status(operationId, "SUCCESSFULLY_DONE")
            # set ns status as INSTANTIATED
            ns_db.set_ns_status(nsId, "INSTANTIATED")
        else:
            log_queue.put(["ERROR", "NS Instantiation FAILED"])
            operation_db.set_operation_status(operationId, "FAILED")
            # set ns status as FAILED
            ns_db.set_ns_status(nsId, "FAILED")

    log_queue.put(["INFO", "INSTANTIATION FINISHED :)"])


def scale_ns(nsId, nsd_json, vnfds_json, request, current_df, current_il):
    # all intelligence delegated to wrapper
    coreMano = createWrapper()
    scaled_vnfs_info = {}
    placement_info = nsir_db.get_placement_info(nsId)
    [scaled_vnfs_info, scale_ops] = coreMano.scale_ns(nsId, nsd_json, vnfds_json, request, current_df, current_il, placement_info)
    if (scaled_vnfs_info is not None) and ("sapInfo" in scaled_vnfs_info):
        log_queue.put(["DEBUG", "ROOE: SCALING updating nsi:%s sapInfo %s" % (nsId, scaled_vnfs_info["sapInfo"])])
        ns_db.save_sap_info(nsId, scaled_vnfs_info["sapInfo"])
    # update list of VLs to be deployed
    [vls_info, vls_to_remove] = update_vls_info_mtp(nsId, scale_ops)
    
    # ask network execution engine to update the virtual links
    eenet.update_vls(nsId, vls_info, vls_to_remove)

    # set operation status as SUCCESSFULLY_DONE
    operationId = operation_db.get_operationId(nsId, "INSTANTIATION")
    if scaled_vnfs_info is not None:
        log_queue.put(["DEBUG", "NS Scaling finished correctly"])
        operation_db.set_operation_status(operationId, "SUCCESSFULLY_DONE")
        # update the IL in the database after finishing correctly the operations
        target_il = extract_target_il(request)
        ns_db.set_ns_il(nsId, target_il)
        # set ns status as INSTANTIATED
        ns_db.set_ns_status(nsId, "INSTANTIATED")
    else:
        log_queue.put(["ERROR", "NS Scaling FAILED"])
        operation_db.set_operation_status(operationId, "FAILED")
        # set ns status as FAILED
        ns_db.set_ns_status(nsId, "FAILED")

    log_queue.put(["INFO", "SCALING FINISHED :)"])


def terminate_ns(nsId):
    """
    Function description
    Parameters
    ----------
    param1: type
        param1 description
    Returns
    -------
    name: type
        return description
    """
    log_queue.put(["INFO", "*****Time measure: ROE Starting ROE processing to terminate"])
    if (nsId.find('_') == -1):
        status = ns_db.get_ns_status(nsId)
        ns_db.set_ns_status(nsId, "TERMINATING")
    else:
        status = "INSTANTIATED"
    # tell the eenet to release the links
    # line below commented until mtp is ready

    if (status != "FAILED"):
        # if it has failed, the MANO platform should have cleaned the deployment and
        # no any logical link has been established
    
        # tell the mano to terminate
        coreMano = createWrapper()
        coreMano.terminate_ns(nsId)
        log_queue.put(["INFO", "*****Time measure: ROE ROE, terminated VNFs"])
        # ask network execution engine to deploy the virtual links
        eenet.uninstall_vls(nsId)
        log_queue.put(["INFO", "*****Time measure: ROE ROE, terminated VLs at MTP"])

    # remove the information from the nsir
    nsir_db.delete_nsir_record(nsId)

    # set operation status as SUCCESSFULLY_DONE
    if (nsId.find('_') == -1):
        # update service status in db
        ns_db.set_ns_status(nsId, "TERMINATED")
        #the service is single, I can update the operationId and the status
        log_queue.put(["INFO", "Removing a single NS"])
        operationId = operation_db.get_operationId(nsId, "TERMINATION")
        operation_db.set_operation_status(operationId, "SUCCESSFULLY_DONE")
    log_queue.put(["INFO", "TERMINATION FINISHED :)"])

