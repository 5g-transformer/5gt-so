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
from http.client import HTTPConnection
from six.moves.configparser import RawConfigParser
from uuid import uuid4
import json
import logging
import itertools

# project imports
from sm.rooe.pa import pa
from db.ns_db import ns_db
from db.operation_db import operation_db
from db.nsir_db import nsir_db
from db.resources_db import resources_db
from coreMano.coreManoWrapper import createWrapper
from sm.eenet import eenet
from nbi import log_queue


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
    nsd = {"nsd": {"Id": "", "name": "", "VNFs": [], "VNFLinks": [],
                   "max_latency": 0, "target_availability": 0, "max_cost": 0}}
    VLs = {}
    max_latency = 0.0

    NSD = nsd_json
    vnfds = vnfds_json

    flavourId = body.flavour_id
    nsLevelId = body.ns_instantiation_level_id

    ID = NSD["nsd"]["nsdIdentifier"]
    name = NSD["nsd"]["nsdName"]
    nsd["nsd"]["Id"] = str(ID)
    nsd["nsd"]["name"] = str(name)

    nsDf = NSD["nsd"]["nsDf"]
    for i in range(len(nsDf)):
        if nsDf[i]["nsDfId"] == flavourId:
            for k in nsDf[i].keys():
                if k == "nsInstantiationLevel":
                    nsInstantiationLevel = nsDf[i][k]
                    for i in range(len(nsInstantiationLevel)):
                        for k1 in nsInstantiationLevel[i].keys():
                            if k1 == "nsLevelId":
                                if nsInstantiationLevel[i][k1] == nsLevelId:
                                    vnfToLevelMapping = nsInstantiationLevel[i]["vnfToLevelMapping"]
                                virtualLinkToLevelMapping = nsInstantiationLevel[i]["virtualLinkToLevelMapping"]
    for i in range(len(vnfToLevelMapping)):
        vnf = vnfToLevelMapping[i]["vnfProfileId"]
        numberOfInstances = vnfToLevelMapping[i]["numberOfInstances"]
        for t in range(len(nsDf)):
            for j in nsDf[t].keys():
                if j == "vnfProfile":
                    vnfProfile = nsDf[t][j]
                    for w in range(len(vnfProfile)):
                        for v in vnfProfile[w].keys():
                            if vnfProfile[w][v] == vnf:
                                vnfdId = vnfProfile[w]["vnfdId"]
                                for vId in vnfds.keys():
                                    # for k in range(len(vnfds["vnfds"])):
                                    if vId == vnfdId:
                                        virtualComputeDesc = vnfds[vId]["virtualComputeDesc"]
                                        for x in range(len(virtualComputeDesc)):
                                            memory = virtualComputeDesc[x]["virtualMemory"]["virtualMemSize"]
                                            cpu = virtualComputeDesc[x]["virtualCpu"]["numVirtualCpu"]
                                        virtualStorageDesc = vnfds[vId]["virtualStorageDesc"]
                                        for x in range(len(virtualStorageDesc)):
                                            storage = virtualStorageDesc[x]["sizeOfStorage"]
                                        nsd["nsd"]["VNFs"].append({"VNFid": str(vnfdId), "instances": numberOfInstances,
                                                                   "location": {"center": {"longitude": 0,
                                                                                           "latitude": 0},
                                                                                "radius": 0},
                                                                   "requirements": {"cpu": cpu,
                                                                                    "ram": memory,
                                                                                    "storage": storage},
                                                                   "failure_rate": 0,
                                                                   "processing_latency": 0})

                                nsVirtualLinkConnectivity = vnfProfile[w]["nsVirtualLinkConnectivity"]

                                for vl in range(len(nsVirtualLinkConnectivity)):
                                    virtualLinkProfileId = nsVirtualLinkConnectivity[vl]["virtualLinkProfileId"]
                                    VLs.setdefault(vnfdId, []).append(virtualLinkProfileId)
    endpoints = list(itertools.combinations(VLs.keys(), 2))
    for i in range(len(endpoints)):
        bw = 0
        latency = 0.0
        profileID = [element for element in (VLs[endpoints[i][0]]) if element in (VLs[endpoints[i][1]])]
        if profileID:
            for i in range(len(virtualLinkToLevelMapping)):
                if profileID[0] == virtualLinkToLevelMapping[i]["virtualLinkProfileId"]:
                    bw = int(virtualLinkToLevelMapping[i]["bitRateRequirements"]["root"])
                for m in range(len(nsDf[0]["virtualLinkProfile"])):
                    if nsDf[0]["virtualLinkProfile"][m]["virtualLinkProfileId"] == profileID[0]:
                        virtualLinkDescId = nsDf[0]["virtualLinkProfile"][m]["virtualLinkDescId"]
                        virtualLinkDesc = NSD["nsd"]["virtualLinkDesc"]
                        for i in range(len(virtualLinkDesc)):
                            if virtualLinkDesc[i]["virtualLinkDescId"] == virtualLinkDescId:
                                latency = virtualLinkDesc[i]["virtualLinkDf"][0]["qos"]["latency"]
            max_latency += latency
            nsd["nsd"]["VNFLinks"].append({"source": str(endpoints[i][0]), "destination": str(
                endpoints[i][1]), "required_capacity": bw, "required_latency": latency, "vlId": virtualLinkDescId,
                "traversal_probability": 1})
            nsd["nsd"]["max_latency"] = max_latency
            nsd["nsd"]["target_availability"] = 1
            nsd["nsd"]["max_cost"] = 1
    return nsd


def get_mtp_resources():
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
    # read mtp properties
    config = RawConfigParser()
    config.read("../../mtp.properties")
    mtp_ip = config.get("MTP", "mtp.ip")
    mtp_port = config.get("MTP", "mtp.port")
    mtp_path = config.get("MTP", "mtp.path")
    mtp_uri = "http://" + mtp_ip + ":" + mtp_port + mtp_path + "/resources"
    # connect to MTP aznd make the request
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    resources = {}
    # code below commented until MTP is ready
    try:
        conn = HTTPConnection(mtp_ip, mtp_port)
        conn.request("GET", mtp_uri, None, header)
        rsp = conn.getresponse()
        resources = rsp.read()
        resources = resources.decode("utf-8")
        log_queue.put(["DEBUG", "Resources from MTP are:"])
        log_queue.put(["DEBUG", resources])
        resources = json.loads(resources)
        log_queue.put(["DEBUG", "Resources from MTP are:"])
        log_queue.put(["DEBUG", json.dumps(resources, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the MTP server is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the MTP server is not running or the connection configuration is wrong"])
    return resources


def extract_vls_info_mtp(resources, extracted_info, placement_info):
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
    # vls_info will be a list of LL to be deployed where each LL is a json
    # according the input body that the mtp expects.
    vls_info = []
    # for each LL in the placment info, get its properties and append it to the vls_info list

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
    # parse the extracted info to have a more usable data structure of VLs info

    log_queue.put(["DEBUG", "ll_resource is:"])
    log_queue.put(["DEBUG", json.dumps(ll_resources, indent=4)])

    vls_properties = {}
    for vl in extracted_info["nsd"]["VNFLinks"]:
        vlId = vl["vlId"]
        vls_properties[vlId] = {}
        vls_properties[vlId]["reqBandwidth"] = vl["required_capacity"]
        vls_properties[vlId]["reqLatency"] = vl["required_latency"]

    # for now we are deplouying one LL per request
    for ll in placement_info["usedLLs"]:
        llId = ll["LLID"]
        for vl in ll["mappedVLs"]:  # vl is the VL Id
            ll_info = {"interNfviPopNetworkType": "",
                       "networkLayer": "",
                       "reqBandwidth": 0,
                       "reqLatency": 0,
                       "metaData": [],
                       "logicalLinkPathList": [
                           {
                               "logicalLinkAttributes": {
                                   "dstGwIpAddress": "",
                                   "localLinkId": 0,
                                   "logicalLinkId": "",
                                   "remoteLinkId": 0,
                                   "srcGwIpAddress": ""
                               }
                           }
                       ]
                       }
            ll_info["interNfviPopNetworkType"] = ll_resources[llId]["interNfviPopNetworkType"]
            ll_info["networkLayer"] = ll_resources[llId]["networkLayer"]
            ll_info["reqBandwidth"] = vls_properties[vl]["reqBandwidth"]
            ll_info["reqLatency"] = vls_properties[vl]["reqLatency"]
            ll_info["logicalLinkPathList"][0]["logicalLinkAttributes"]["dstGwIpAddress"] = \
                ll_resources[llId]["dstGwIpAddress"]
            ll_info["logicalLinkPathList"][0]["logicalLinkAttributes"]["srcGwIpAddress"] = \
                ll_resources[llId]["srcGwIpAddress"]
            ll_info["logicalLinkPathList"][0]["logicalLinkAttributes"]["remoteLinkId"] = \
                ll_resources[llId]["remoteLinkId"]
            ll_info["logicalLinkPathList"][0]["logicalLinkAttributes"]["localLinkId"] = \
                ll_resources[llId]["localLinkId"]
            ll_info["logicalLinkPathList"][0]["logicalLinkAttributes"]["logicalLinkId"] = llId
            vls_info.append(ll_info)

    log_queue.put(["DEBUG", "VLS_info for eenet is:"])
    log_queue.put(["DEBUG", json.dumps(vls_info, indent=4)])

    return vls_info


def instantiate_ns(nsId, nsd_json, vnfds_json, request):
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
    # extracted_info = extract_nsd_info_for_pa(nsd_json, vnfds_json, request)
    extracted_info = extract_nsd_info_for_pa(nsd_json, vnfds_json, request)
    log_queue.put(["DEBUG", "NSD extracted info for PA is:"])
    log_queue.put(["DEBUG", json.dumps(extracted_info, indent=4)])
    # first get mtp resources and lock db
    resources = get_mtp_resources()

    # ask pa to calculate the placement - read pa config from properties file
    config = RawConfigParser()
    config.read("../../sm/rooe/rooe.properties")
    pa_ip = config.get("PA", "pa.ip")
    pa_port = config.get("PA", "pa.port")
    pa_path = config.get("PA", "pa.path")
    pa_uri = "http://" + pa_ip + ":" + pa_port + pa_path
    # ask pa to calculate the placement - prepare the body
    paId = str(uuid4())
    body = {"ReqId": paId,
            "nfvi": resources,
            "nsd": extracted_info,
            "callback": "http://localhost:8080/5gt/so/v1/__callbacks/pa/" + paId}

    # ask pa to calculate the placement - do request
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    placement_info = {}
    # code below is commented until PA is ready
#     try:
#         conn = HTTPConnection(pa_ip, pa_port)
#         conn.request("POST", pa_uri, body, header)
#
#         # ask pa to calculate the placement - read response and close connection
#         rsp = self.conn.getresponse()
#         placement_info = rsp.read()
#         conn.close()
#     except ConnectionRefusedError:
#         # the PA server is not running or the connection configuration is wrong
#         log_queue.put(["ERROR", "the PA server is not running or the connection configuration is wrong"])
    placement_info = {
        "usedNFVIPops": [{"NFVIPoPID": "openstack-site29_Zona1_w", "mappedVNFs": ["webserver", "spr21"]},
                         {"NFVIPoPID": "openstack-site31_w", "mappedVNFs": ["spr1"]}],
        "usedLLs": [{"LLID": "151515", "mappedVLs": ["VideoData"]}],
        "usedVLs": [{"NFVIPoP": "openstack-site29_Zona1_w", "mappedVLs": ["VideoDistribution"]},
                    {"NFVIPoP": "openstack-site31_w", "mappedVLs": ["mgt"]}],
        "totalLatency": 1.3
    }

    # save placement info in database
    nsir_db.save_placement_info(nsId, placement_info)

    # ask cloudify/OSM to deploy vnfs
    coreMano = createWrapper()
    deployed_vnfs_info = {}
    deployed_vnfs_info = coreMano.instantiate_ns(nsId, nsd_json, body, placement_info)
    if deployed_vnfs_info is not None and "sapInfo" in deployed_vnfs_info:
        log_queue.put(["DEBUG", "rooe: updating nsi:%s sapInfo" % nsId])
        ns_db.save_sap_info(nsId, deployed_vnfs_info["sapInfo"])

    # list of VLs to be deployed
    vls_info = extract_vls_info_mtp(resources, extracted_info, placement_info)

    # ask network execution engine to deploy the virtual links
    # line below commented until mtp is ready
#     eenet.deploy_vls(vls_info, nsId)

    # set operation status as SUCCESSFULLY_DONE
    operationId = operation_db.get_operationId(nsId, "INSTANTIATION")
    if deployed_vnfs_info is not None:
        log_queue.put(["DEBUG", "NS Instantiation finished correctly"])
        operation_db.set_operation_status(operationId, "SUCCESSFULLY_DONE")
        # set ns status as INSTANTIATED
        ns_db.set_ns_status(nsId, "INSTANTIATED")
    else:
        log_queue.put(["ERROR", "NS Instantiation FAILED"])
        operation_db.set_operation_status(operationId, "FAILED")
        # set ns status as FAILED
        ns_db.set_ns_status(nsId, "FAILED")


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

    # check if placement info has been saved in nsri database and update the resources database
    if nsir_db.exists_nsir(nsId):
        placement_info = nsir_db.get_placement_info(nsId)
        resources_db.add_resources_information(placement_info)

    # tell the eenet to release the links
    # line below commented until mtp is ready
#     eenet.uninstall_vls(nsId)

    # tell the mano to terminate
    coreMano = createWrapper()
    coreMano.terminate_ns(nsId)

    # update service status in db
    ns_db.set_ns_status(nsId, "TERMINATED")

    # set operation status as SUCCESSFULLY_DONE
    operationId = operation_db.get_operationId(nsId, "TERMINATION")
    operation_db.set_operation_status(operationId, "SUCCESSFULLY_DONE")
