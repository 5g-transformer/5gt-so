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
This file implements the Service Orchestration Engine Parent (soep): for federation purposes.
"""

# python imports
from uuid import uuid4
from multiprocessing import Process, Queue
from pymongo import MongoClient
from json import dumps, loads, load
from six.moves.configparser import RawConfigParser
from http.client import HTTPConnection
import sys
import time
import wget
import tarfile
import os
import copy
import socket

# project imports
from db.ns_db import ns_db
from db.nsd_db import nsd_db
from db.vnfd_db import vnfd_db
from db.appd_db import appd_db
from db.operation_db import operation_db
from sm.soe import soe
from nbi import log_queue
from monitoring import monitoring, alert_configure
from sm.crooe import crooe

# dict to save processes by its nsId
processes_parent = {}

# dict with the IP of the federated domains. Assuming they are using a 5GT-arch
fed_domain= {}
available_VS = []
config = RawConfigParser()
config.read("../../sm/soe/federation.properties")
number_fed_domains= int(config.get("FEDERATION", "number"))
for i in range (1,number_fed_domains+1):
  domain = "Provider"+str(i)
  try:
    fed_domain[domain] = socket.gethostbyname(config.get("FEDERATION", domain))
  except socket.gaierror:
      print(["Error", "Federation domain was not found %s" % (domain)])
#log_queue.put(["DEBUG", "SOEp reading federated domains: %s" % (fed_domain)])

ewbi_port=config.get("FEDERATION", "ewbi_port")
ewbi_path=config.get("FEDERATION", "ewbi_path")

config.read("../../sm/soe/vs.properties")
number_vs= int(config.get("VS", "number"))
for i in range(1, number_vs+1):
    vs = "VS"+str(i)
    try:
        vs_name = config.get("VS", vs)
        addr = socket.gethostbyname(vs_name)
    except socket.gaierror:
        addr = "127.0.0.1"
        print(["Error",  vs + " with name: %s was not found" % (vs_name)])
        print(["Error", vs + " will be use %s" % (addr)])
    available_VS.append(addr)
# log_queue.put(["DEBUG", "SOEp reading available_VS: %s" % (available_VS)])

# Parameters for HTTP Connection
port = "8080"
headers = {'Content-Type': 'application/json',
           'Accept': 'application/json'}
timeout = 10

########################################################################################################################
# PRIVATE METHODS                                                                                                      #
########################################################################################################################

def check_df_compatibilities(nested_record, composite_nsd_json, body):
    """
    Function description
    Parameters
    ----------
    nested_record: dict
        Record of the nested service that you want to attach you. Extracted from ns_db.Identifier of the service
    composite_nsd_json: dict
        Nsd json of the composite network service .
    body: struct
        Body of the request where we will extract the requested deployment flavour and instantiation level 
    Returns
    -------
    BooleanTrue or False
        True: when the deployment flavour and instantiation level of the nested and the composite are compatible
        False: otherwise
    """
    nested_il = nested_record["nsInstantiationLevelId"]
    composite_df = body.flavour_id
    composite_il = body.ns_instantiation_level_id
    for df in composite_nsd_json["nsd"]["nsDf"]:
        log_queue.put(["DEBUG", "df evaluated: %s"%(df["nsDfId"]) ])
        if (df["nsDfId"] == composite_df):
            for il in df["nsInstantiationLevel"]:
                if (il["nsLevelId"] == composite_il):
                    for nsmap in il["nsToLevelMapping"]:
                        # look for the one that coincides with the nested
                        for nsprof in df["nsProfile"]:
                            if nsprof["nsProfileId"] == nsmap["nsProfileId"]:
                                if (nsprof["nsInstantiationLevelId"] == nested_il):
                                    return True
    return False

def define_new_body_for_composite(nsId, nsdId, body):
    """
    Function description
    Parameters
    ----------
    nsId: string
        Identifier of the service
    body: struct
        Object having the deployment flavour and the instantiation level.
    nsdId: string
        Identifier of the nested service to be instantiated, only available when 
    Returns
    -------
    name: struct
        Object with the appropriate df and il according to the request
    """
    body_tmp = copy.deepcopy(body)
    # get the nsdId that corresponds to nsId
    nsdcId = ns_db.get_nsdId(nsId)
    nsd_json = nsd_db.get_nsd_json(nsdcId, None)
    if "nestedNsdId" not in nsd_json["nsd"].keys():
        # we are delegating a single nested service, so the body is already the passed one
        return body
    flavourId = body_tmp.flavour_id
    nsLevelId = body_tmp.ns_instantiation_level_id
    for df in nsd_json["nsd"]["nsDf"]:
        if (df["nsDfId"] == flavourId):
            for il in df["nsInstantiationLevel"]:
                if (il["nsLevelId"] == nsLevelId):
                    #here we have to distinguish between composite NSD and single NSD
                    for nsProfile in il["nsToLevelMapping"]:
                        nsp = nsProfile["nsProfileId"]
                        for nsprof in df["nsProfile"]:
                            if ( (nsprof["nsProfileId"] == nsp) and (nsprof["nsdId"] == nsdId) ):
                                body_tmp.flavour_id = nsprof["nsDfId"]
                                body_tmp.ns_instantiation_level_id = nsprof["nsInstantiationLevelId"]
                                return body_tmp


def exists_nsd(nsdId):
    """
    Function to check if an NSD with identifier "nsdId" exists.
    Parameters
    ----------
    nsdId: string
        Identifier of the Network Service Descriptor
    Returns
    -------
    boolean
        returns True if a NSD with Id "nsdId" exists in the Service Catalog. Returns False otherwise.
    """
    return nsd_db.exists_nsd(nsdId)

def create_operation_identifier(nsId, operation_type):
    """
    Creates an operation identifierFunction description
    Parameters
    ----------
    param1: type
        param1 description
    Returns
    -------
    name: type
        return description
    """
    operationId = str(uuid4())
    operation_db.create_operation_record(operationId, nsId, operation_type)
    return operationId


def create_operation_identifier_provider(nsd, name, description):
    path = "/5gt/so/v1/ns"
    key = next(iter(nsd["domain"]))
    data = {"nsDescription": "Federating service: " + description,
            "nsName": "Consumer " + key + ": " + name, #check this name, can be an arbitrary one? !!!
            "nsdId": nsd["nsd"]
            }
    # we open here the connection and we will close when the process is finished
    # port, headers and timeout defined previously
    conn = HTTPConnection(nsd["domain"][key], port, timeout=timeout)
    conn.request("POST", path, dumps(data), headers)
    conn.sock.settimeout(timeout)
    rsp = conn.getresponse()
    data = rsp.read().decode()
    data = loads(data)
    nsId = data["nsId"]
    return [nsId, conn]

def instantiate_ns_provider (nsId_n, conn, body, additionalParams=None):
    # instantiate the service
    path = "/5gt/so/v1/ns/" + nsId_n + "/instantiate"
    if additionalParams:
        data = {"flavourId": body.flavour_id, 
                "nsInstantiationLevelId": body.ns_instantiation_level_id,
                "additionalParamForNs" : additionalParams
               }
    else:
        data = {"flavourId": body.flavour_id,
                "nsInstantiationLevelId": body.ns_instantiation_level_id
               }
    conn.request("PUT", path, dumps(data), headers)
    conn.sock.settimeout(timeout)
    rsp = conn.getresponse()
    data = rsp.read().decode()
    data = loads(data)
    operationId = data["operationId"]
    return operationId

def scale_ns_provider (nsId_n, body, domain, additionalParams=None):
    #scale the service
    path = "/5gt/so/v1/ns/" + nsId_n + "/scale"
    target_il = None
    operationId = ""
    conn = ""
    key = next(iter(domain))
    if (body.scale_type == "SCALE_NS"):
        target_il = body.scale_ns_data.scale_ns_to_level_data.ns_instantiation_level
    if not target_il == None:
        data = {  "scaleType": "SCALE_NS",
                  "scaleNsData": {
                      "scaleNsToLevelData": {
                          "nsInstantiationLevel": target_il
                      }
                  }
                }
        conn = HTTPConnection(domain[key], port, timeout=timeout)
        conn.request("PUT", path, dumps(data), headers)
        conn.sock.settimeout(timeout)
        rsp = conn.getresponse()
        data = rsp.read().decode()
        data = loads(data)
        operationId = data["operationId"]
    return [operationId, conn, target_il]


def terminate_ns_provider(nsId, domain):
    # terminate the service
    path = "/5gt/so/v1/ns/" + nsId + "/terminate"
    key = next(iter(domain))
    conn = HTTPConnection(domain[key], port, timeout=timeout)
    conn.request("PUT", path, None, headers)
    conn.sock.settimeout(timeout)
    rsp = conn.getresponse()
    data = rsp.read().decode()
    data = loads(data)
    operationId = data["operationId"]
    return [operationId, conn]

def get_operation_status_provider(operationId, conn):
    path = "/5gt/so/v1/operation/" + operationId
    conn.request("GET", path, None, headers)
    conn.sock.settimeout(timeout)
    rsp = conn.getresponse()
    data = rsp.read().decode()
    log_queue.put(["INFO", "get_operation_status_provider data: %s" % (data)])
    data = loads(data)
    return data['status']

def get_sap_info_provider(nsId_n, conn): 
    path = "/5gt/so/v1/ns/" + nsId_n
    conn.request("GET", path, None, headers)
    conn.sock.settimeout(timeout)
    rsp = conn.getresponse()
    data = rsp.read().decode()
    data = loads(data)
    sapInfo = data["queryNsResult"][0]["sapInfo"]
    conn.close()
    return sapInfo


def generate_nested_sap_info(nsId, nsd_name):
    """
    Returns the information of the Network Service Instance identified by nsId.
    Parameters
    ----------
    nsId: string
        Identifier of the NS instance to get information.
    nsd_name: string
        Identifier of the NS descriptor to get information
    Returns
    -------
    dict
        Formatted information of the Network Service Instance info.
    """

    nsd_json = nsd_db.get_nsd_json(nsd_name)
    if "sapd" in nsd_json["nsd"]:
        total_sap_info = get_ns_sap_info(nsId,nsd_json["nsd"]["sapd"])
        if total_sap_info is not None:
            return total_sap_info
        else: 
            return None

def instantiate_ns_process(nsId, body, requester):
    """
    The process to instantiate the Network Service associated to the instance identified by "nsId".
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    body: request body
    requester: string
        IP address of the requester, needed for federation purposes
    Returns
    -------
    None
    """
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp decomposing NS"])
    # get the nsdId that corresponds to nsId
    nsdId = ns_db.get_nsdId(nsId)
    # first get the ns and vnfs descriptors
    nsd_json = nsd_db.get_nsd_json(nsdId, None)
    local_services = []
    federated_services = []
    nested_services = []
    if "nestedNsdId" in nsd_json["nsd"].keys():
        # I have a list of services within the nsd_json: composite
        # currently, not valid the request of a composite in a federated domain
        for nested in nsd_json["nsd"]["nestedNsdId"]:
            nested_services.append(nested)
    else: 
        #two options here:
        # 1) this is a single one that is delegated to other domain, consumer send to provider
        # 2) this is a single nested that is a reques from a consumer domain, provider receiver a consumer request
        nested_services.append(nsd_json["nsd"]["nsdIdentifier"])
    for ns in nested_services:
        domain = nsd_db.get_nsd_domain(ns, None)
        if (domain == "local"):
            local_services.append({"nsd":ns, "domain": domain})
        else:
            federated_services.append({"nsd":ns, "domain": domain})
    log_queue.put(["INFO", "SOEp instantiate_ns_process with nsId %s, body %s" % (nsId, body)])
    index = 0

    # in case we have a nestedId, we need to check its deployment flavour to check if it compatible with the one of the composite
    nested_instance = {}
    if body.nested_ns_instance_id:
        # it has been previously checked if exists and it is in INSTATIATED state and that it can be shared
        nested_record = ns_db.get_ns_record(body.nested_ns_instance_id[0])
        if not (check_df_compatibilities(nested_record, nsd_json, body)):
            return 404
        else:
            # link to possible nested instances we need to update the original registry
            ns_db.set_ns_nested_services_ids(nsId, body.nested_ns_instance_id[0])
            # we need to remove this nested service from the local or federated list
            # for the moment, not contemplated compsition with a nested federated/delegated one
            # then the nested will be in local
            for nsd in local_services:
                if (nsd["nsd"] == nested_record["nsd_id"]):
                    nested_instance[nsd["nsd"]] = body.nested_ns_instance_id[0]
                    local_services.remove(nsd)
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp finished decomposing NS and checking references"])
    if "nestedNsdId" in nsd_json["nsd"].keys():
        [network_mapping, renaming_networks] = crooe.mapping_composite_networks_to_nested_networks(nsId, nsd_json, body, nested_instance) 
    else:
        # it is a single delegated NS
        network_mapping = {}
        renaming_networks = {}

    log_queue.put(["INFO", "*****Time measure: SOEp CROOE finished checking interconnection nested NS and checking references"])
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp instantiating local nested NSs"])
    for nsd in local_services:
        log_queue.put(["INFO", "*****Time measure: SOEp instantiating local nested NSs %s"%index])
        if (requester != "local"):
            # in that case, we only iterate once, this is the part of the federated service in the provider domain
            networkInfo = crooe.get_federated_network_info_request(body.additional_param_for_ns["nsId"], 
                          nsd['nsd'], requester, ewbi_port, ewbi_path)
            log_queue.put(["INFO", "*****Time measure: SOEp SOEp receiving networkInfo from local CROOE for nested with index %s"%index])
            log_queue.put(["INFO", "SOEp getting information of the consumer domain from the EWBI: %s" %networkInfo])
            # we need to save the network_mapping for a next iteration with the ewbi after the federated service has been instantiated
            log_queue.put(["INFO", "SOEp passing info to instantiate_ns_process"])
            log_queue.put(["INFO", dumps({nsd["nsd"]:[loads(body.additional_param_for_ns["network_mapping"]), networkInfo]},indent=4)])
            soe.instantiate_ns_process(nsId, body, {nsd["nsd"]:[loads(body.additional_param_for_ns["network_mapping"]), networkInfo]})
        else: 
            # new_body = soe.define_new_body_for_composite(nsId, nsd["nsd"], body) #be careful with the pointer
            nested_body = define_new_body_for_composite(nsId, nsd["nsd"], body) #be careful with the pointer
            nsId_nested = nsId + '_' + nsd["nsd"]
            # we have to create the info entry before to have a place where to store the sap_info
            info = { "nested_instance_id": nsId_nested,
                     "domain": "local",
                     "instantiation_order": index,
                     "nested_id": nsd["nsd"],
                     "nested_df": nested_body.flavour_id,
                     "nested_il": nested_body.ns_instantiation_level_id,
                   }   
            ns_db.update_nested_service_info(nsId, info, "push") 
            soe.instantiate_ns_process(nsId, nested_body, {nsd["nsd"]:[network_mapping['nestedVirtualLinkConnectivity'][nsd["nsd"]]]})
            # the service is instantiated
            sapInfo = generate_nested_sap_info(nsId, nsd["nsd"])
            if (sapInfo == None):
                # there has been a problem with the nested service and the process failed, we have 
                # to abort the instantiation
                operationId = operation_db.get_operationId(nsId, "INSTANTIATION")
                operation_db.set_operation_status(operationId, "FAILED")
                # set ns status as FAILED
                ns_db.set_ns_status(nsId, "FAILED")
                # remove the reference previously set
                if body.nested_ns_instance_id:
                    ns_db.delete_ns_shared_services_ids(body.nested_ns_instance_id[0], nsId)
                return #stop instantiating: to do: to manage in case of failure

            info = { "status": "INSTANTIATED", #as it is coming back after instantiating
                     "sapInfo": sapInfo
                   }
            log_queue.put(["INFO", "Nested NS service instantiated with info: "])
            log_queue.put(["INFO", dumps(info,indent=4)])
            ns_db.update_nested_service_info(nsId, info, "set", nsId_nested)
            log_queue.put(["INFO", "*****Time measure: SOEp SOEp finishing instantiating local nested NSs %s"%index])
            index = index + 1
            # clean the sap_info of the composite service, 
            ns_db.save_sap_info(nsId, "")
        
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp finished instantiating local nested NSs"])
    if (requester != "local"):            
    # now I can return since the rest of interaction with the consumer domain will be done through the EWBI interface
        log_queue.put(["INFO", "SOEp instantiate_ns_process returning because the rest of the interactions"])
        log_queue.put(["INFO", "of the federated service are done through the EWBI interface directed by consumer"])
        return

    # federated_instance_info = []
    
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp instantiating federated nested NSs"])
    for nsd in federated_services:
        log_queue.put(["INFO", "*****Time measure: SOEp SOEp instantiating federated nested NSs %s"%index])
        # steps:
        # 1) ask for an ns identifier to the remote domain
        name = ns_db.get_ns_name(nsId)
        description = ns_db.get_ns_description(nsId)
        [nsId_n, conn] = create_operation_identifier_provider(nsd, name, description)
        # 2) ask for the service with the provided id in step 1)
        nested_body = define_new_body_for_composite(nsId, nsd["nsd"], body)
        log_queue.put(["INFO", "SOEp generating federated nested_body: %s" % (nested_body)])
        log_queue.put(["INFO", "*****Time measure: SOEp SOEp generating request for federated domain for nested %s"%index])
        if (len(nested_services) == 1 and len(federated_services) == 1):
            # it means it is a single delegated NS
            operationId = instantiate_ns_provider (nsId_n, conn, nested_body)
            log_queue.put(["INFO", "*****Time measure: SOEp SOEp receiving operationId of federated nested %s"%index])
        else:
            federated_mapping = {"nsId": network_mapping["nsId"], "network_mapping": dumps(network_mapping["nestedVirtualLinkConnectivity"][nsd["nsd"]])}
            operationId = instantiate_ns_provider (nsId_n, conn, nested_body, federated_mapping)
            log_queue.put(["INFO", "*****Time measure: SOEp SOEp receiving operationId of federated nested %s"%index])
        status = "INSTANTIATING"
        # 3) enter in a loop to wait until service is instantiated, checking with the operationid, that the operation 
        # 4) update the register of nested services instantiated
        while (status != "SUCCESSFULLY_DONE"):		
            status = get_operation_status_provider(operationId, conn)
            if (status == 'FAILED'):
                operationIdglobal = operation_db.get_operationId(nsId, "INSTANTIATION")
                operation_db.set_operation_status(operationIdglobal, "FAILED")
                # set ns status as FAILED
                ns_db.set_ns_status(nsId, "FAILED")
                # remove the reference previously set
                if body.nested_ns_instance_id:
                    ns_db.delete_ns_shared_services_ids(body.nested_ns_instance_id[0], nsId)
                return #stop instantiating: to do: to manage in case of failure
            time.sleep(10)      
        log_queue.put(["DEBUG", "SOEp COMPLETE operationId: %s" % (operationId)])
        # 5) ask the federated domain about its instantiation in case it is not a single delegated NS
        federated_info = {}
        if not (len(nested_services) == 1 and len(federated_services) == 1):
            # it means it is not a single delegated NS
            key = next(iter(nsd["domain"]))
            log_queue.put(["INFO", "SOEp asking instantiation parameters of %s to %s"%(nsd["nsd"],nsd["domain"][key])]) 
            log_queue.put(["INFO", "*****Time measure: SOEp SOEp asking instantiation result to federated CROOE of federated nested NSs %s"%index])
            federated_info = crooe.get_federated_network_instance_info_request(nsId_n, nsd["nsd"], nsd["domain"][key], ewbi_port, ewbi_path)
            log_queue.put(["INFO", "*****Time measure: SOEp SOEp receiving instantiation result to federated CROOE of federated nested NSs %s"%index])
            log_queue.put(["INFO", "SOEp obtained federatedInfo through EWBI: %s"%federated_info])
        # finally this information is relevant for subsequent instantiations
        # 6) update the local registry about information of the federated nested service
        sap_info =  get_sap_info_provider(nsId_n, conn) # we close here the connection
        info = { "nested_instance_id": nsId_n,
                 "domain": nsd["domain"],
                 "instantiation_order": index,
                 "nested_id": nsd["nsd"],
                 "nested_df": nested_body.flavour_id,
                 "nested_il": nested_body.ns_instantiation_level_id,
                 "status": "INSTANTIATED",
                 "federatedInstanceInfo": federated_info,
                 "sapInfo": sap_info
               }
        ns_db.update_nested_service_info(nsId, info, "push")
        log_queue.put(["INFO", "*****Time measure: SOEp SOEp finishing instantiating federated nested NSs %s"%index])
        index = index + 1

    log_queue.put(["DEBUG", "*****Time measure: SOEp SOEp finishing instantiating federated nested NSs"])
    # interconnecting the different nested between them
    log_queue.put(["DEBUG", "*****Time measure: SOEp SOEp interconnecting nested NSs"])
    if (len(nested_services) > 1):
        # in case of one, it means that it is a single delegation and you do not need to connect it
        # at least one of it will be local, so first we connect the local nested services and then we connect them with the federated
        if (len(local_services) > 1 or (len(local_services) == 1 and body.nested_ns_instance_id)):
            log_queue.put(["INFO", "*****Time measure: SOEp SOEp-CROOE interconnecting local nested NSs"])
            crooe.connecting_nested_local_services(nsId, nsd_json, network_mapping, local_services, nested_instance, renaming_networks)
            log_queue.put(["INFO", "*****Time measure: SOEp SOEp-CROOE finishing interconnecting local nested NSs"])
        # once local are connected, connect federated services with the local domain
        if (len(federated_services) > 0):
            log_queue.put(["INFO", "*****Time measure: SOEp SOEp-CROOE interconnecting federated nested NSs"])
            crooe.connecting_nested_federated_local_services(nsId, nsd_json, network_mapping, local_services, federated_services, nested_instance, renaming_networks)
            log_queue.put(["INFO", "*****Time measure: SOEp SOEp-CROOE finishing interconnecting federated nested NSs"])

    # after instantiating all the nested services, update info of the instantiation    
    operationId = operation_db.get_operationId(nsId, "INSTANTIATION")
    ns_record = ns_db.get_ns_record(nsId)
    status = "INSTANTIATED"
    for elem in ns_record["nested_service_info"]:
        log_queue.put(["DEBUG", "SOEp finishing... nested_service_info: %s" % (elem)])
        if not elem["status"] == "INSTANTIATED":
            status = "INSTANTIATING"
            break
    if (status == "INSTANTIATED"):
        log_queue.put(["DEBUG", "NS Instantiation finished correctly"])
        operation_db.set_operation_status(operationId, "SUCCESSFULLY_DONE")
        # set ns status as INSTANTIATED
        ns_db.set_ns_status(nsId, "INSTANTIATED")
 
    # once the service is correctly instantiated, link to possible nested instances
    if (body.nested_ns_instance_id):
        ns_db.set_ns_shared_services_ids(body.nested_ns_instance_id[0], nsId)
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp finishing instantiation"])

def scale_ns_process(nsId, body):
    """
    Performs the scaling of the service identified by "nsId" according to the info at body 
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    body: request body including scaling operation
    Returns
    -------
    """
    # for the moment, we are only managing the scaling of single delegated network service
    nested_service_info = ns_db.get_nested_service_info(nsId)
    # although there is only one
    for ns in range(0, len(nested_service_info)):
        nested_id = ns["nested_instance_id"]
        domain = ns["domain"]
        [operation_id, conn, target_il] = scale_ns_provider(nested_id, body, domain)
        if not target_il == None:
            status = "INSTANTIATING"
            # 3) enter in a loop to wait until service is instantiated, checking with the operationid, that the operation 
            # 4) update the register of nested services instantiated
            while (status != "SUCCESSFULLY_DONE"):		
                status = get_operation_status_provider(operation_id, conn)
                if (status == 'FAILED'):
                    operationIdglobal = operation_db.get_operationId(nsId, "INSTANTIATION")
                    operation_db.set_operation_status(operationIdglobal, "FAILED")
                    # set ns status as FAILED
                    ns_db.set_ns_status(nsId, "FAILED")
                    return #stop instantiating: to do: to manage in case of failure
                time.sleep(10)   
            log_queue.put(["INFO", "SOEp COMPLETE scaling operationId: %s" % (operationId)])
            sap_info =  get_sap_info_provider(nsId_n, conn) # we close here the connection   
            #update the register in the nested
            ns["nested_il"] = target_il
            ns_db.update_nested_service_info(nsId, ns, "set", nested_id)
            #update the register in the global registry
            ns_db.set_ns_il(nsId, target_il)

    # after instantiating all the nested services, update info of the instantiation    
    operationId = operation_db.get_operationId(nsId, "INSTANTIATION")
    ns_record = ns_db.get_ns_record(nsId)
    status = "INSTANTIATED"
    for elem in ns_record["nested_service_info"]:
        if not elem["status"] == "INSTANTIATED":
            status = "INSTANTIATING"
            break
    if (status == "INSTANTIATED"):
        log_queue.put(["DEBUG", "NS Instantiation finished correctly"])
        operation_db.set_operation_status(operationId, "SUCCESSFULLY_DONE")
        # set ns status as INSTANTIATED
        ns_db.set_ns_status(nsId, "INSTANTIATED")


def terminate_ns_process(nsId, aux):
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
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp starting terminating service"])
    log_queue.put(["DEBUG", "SOEp terminating_ns_process with nsId %s" % (nsId)])
    ns_db.set_ns_status(nsId, "TERMINATING")
    nested_record = ns_db.get_ns_record(nsId)
    nested_info = nested_record["nested_service_info"]
    # we have to remove in reverse order of creation (list are ordered in python)
    #for index in range(0, len(nested_info)):
    for index in range(len(nested_info)-1, -1, -1):
        log_queue.put(["INFO", "*****Time measure: SOEp SOEp terminating nested service"])
        nested_service = nested_info[index]
        if (nested_service["domain"] == "local"):
            # local service to be terminated
            nested_service["status"] = "TERMINATING"
            log_queue.put(["INFO", "SOEp eliminating LOCAL nested service: %s"%nested_service["nested_instance_id"]])
            soe.terminate_ns_process(nested_service["nested_instance_id"], None)
            # update the status
            nested_service["status"] = "TERMINATED"
        else:
            # federated service to be terminated
            log_queue.put(["INFO", "SOEp eliminating FEDERATED nested service: %s"%nested_service["nested_instance_id"]])
            [operationId, conn] = terminate_ns_provider(nested_service["nested_instance_id"], nested_service["domain"])
            nested_service["status"] = "TERMINATING"
            status = "TERMINATING"
            while (status != "SUCCESSFULLY_DONE"):		
                status = get_operation_status_provider(operationId, conn)
                if (status == 'FAILED'):
                    operationIdglobal = operation_db.get_operationId(nsId, "TERMINATION")
                    operation_db.set_operation_status(operationIdglobal, "FAILED")
                    # set ns status as FAILED
                    ns_db.set_ns_status(nsId, "FAILED")
                    return #stop instantiating: to do: to manage in case of failure
                time.sleep(10)
            # update the status
            nested_service["status"] = "TERMINATED"
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp finished ALL nested service"])
    #croe remove the local logical links for this composite service (to be reviewed when federation)
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp starting removing nested connections"])
    crooe.remove_nested_connections(nsId)
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp finishing removing nested connections"])

    #now declare the composite service as terminated
    operationId = operation_db.get_operationId(nsId, "TERMINATION")
    status = "TERMINATED"
    for index in range (0, len(nested_info)):
        if not nested_info[index]["status"] == "TERMINATED":
            status = "TERMINATING"
            break
    if (status == "TERMINATED"):
        operation_db.set_operation_status(operationId, "SUCCESSFULLY_DONE")
        log_queue.put(["INFO", "NS Termination finished correctly :)"])
        # set ns status as TERMINATED
        ns_db.set_ns_status(nsId, "TERMINATED")
        # update the possible connections
        if "nestedNsId" in nested_record: 
            nested_instanceId = ns_db.delete_ns_nested_services_ids(nsId)
            ns_db.delete_ns_shared_services_ids(nested_instanceId, nsId)
        # for the 5GT-VS not to break
        # ns_db.delete_ns_record(nsId)
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp finished terminating service"])

########################################################################################################################
# PUBLIC METHODS                                                                                                       #
########################################################################################################################


def create_ns_identifier(body):
    """
    Creates and returns an Identifier for an instance of the NSD identified in the body by the parameter nsd_id.
    Saves the identifier and the information associated in the Network Service Instances DB and sets the status to "NOT
    INSTANTIATED".
    Parameters
    ----------
    body: request
        includes the following fields:
        "nsd_id", string, ifentifier of the NSD
        "ns_name", string, name to be associated to the NS instance
        "ns_description": string, description to be associated to the NS instance
    Returns
    -------
    nsId: string
        Identifier of the Network Service Instance.
    """

    # check nsd exists, return 404 if it doesn"t exist
    log_queue.put(["INFO", "create_ns_identifier for: %s" % body])

    nsd_id = body.nsd_id
    if not exists_nsd(nsd_id):
        return 404
    # create the identifier
    nsId = str(uuid4())
    # for cloudify compatibility it must start with a letter
    # nsId = 'a' + nsId[1:]
    nsId = 'fgt-' + nsId[1:]

    # save to DB
    ns_db.create_ns_record(nsId, body)

    return nsId

def instantiate_ns(nsId, body, requester):
    """
    Starts a process to instantiate the Network Service associated to the instance identified by "nsId".
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    body: request body
    requester: string
        IP address of the entity making the request
    Returns
    -------
    string
        Id of the operation associated to the Network Service instantiation.
    """
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp instantiating a NS"])
    log_queue.put(["INFO", "instantiate_ns for nsId %s with body: %s" % (nsId, body)])
    #client = MongoClient()
    #fgtso_db = client.fgtso
    #ns_coll = fgtso_db.ns

    if not ns_db.exists_nsId(nsId):
        return 404

    status = ns_db.get_ns_status(nsId)
    if status != "NOT_INSTANTIATED":
        return 400

    if body.nested_ns_instance_id:
        #as we only are assuming one level of nesting, the nested_ns_instance_id array will be formed by one nsId
        if not ns_db.exists_nsId(body.nested_ns_instance_id[0]):
            return 404
        nested_status = ns_db.get_ns_status(body.nested_ns_instance_id[0])
        if nested_status != "INSTANTIATED":
            return 400
        # can be shared this nested_ns_instance?
        nsd_shareable = nsd_db.get_nsd_shareability(body.nested_ns_instance_id[0])
        if (nsd_shareable == "False"):
           return 404

    validIP = False
    request_origin = "local"
    log_queue.put(["DEBUG", "SOEp receiving request from: %s"%(requester)])
    # check where the request comes from, either local or from a federated domain
    if requester not in available_VS:
        #it comes from a federated domain
        request_origin = requester
        # now, check if it is a validIP, from a registered federated domain
        for domain in fed_domain.keys():
            if (fed_domain[domain] == requester):
                validIP = True
                log_queue.put(["INFO", "SOEp receiving request from a valid federated domain: %s = (%s)"%(domain,fed_domain[domain])])
    else:
        log_queue.put(["INFO", "SOEp receiving request from a valid local domain"])
        validIP = True
        
    if not validIP:
        # the request comes from a non-authorised origin, discard the request
        return 404

    ns_db.save_instantiation_info(nsId, body, requester)
    operationId = create_operation_identifier(nsId, "INSTANTIATION")
    # two options to delegate to soec: if there is not a reference instance 
    # or if the nsd descriptor does not have "nestedNsdId" field
    # get the nsdId that corresponds to nsId
    nsdId = ns_db.get_nsdId(nsId)
    # first get the ns and vnfs descriptors
    nsd_json = nsd_db.get_nsd_json(nsdId, None)
    domain = nsd_db.get_nsd_domain (nsdId)
    if (domain == "local" and not body.additional_param_for_ns): 
        # when you onboard the single nested ones, you specify the provider (either locar or other)
        # composite network services descriptors domain value is set to composite, so SOEp must handle it
        log_queue.put(["INFO", "SOEp delegating the INSTANTIATION to SOEc"])
        ps = Process(target=soe.instantiate_ns_process, args=(nsId, body))
        ps.start()
        # save process
        soe.processes[operationId] = ps
    else:
        # soep should do things: it is a composite, there is a reference, there is delegation, 
        # it is a request coming from a consumer federated domain
        # update: 19/09/17: For the eHealth usecase, it is considered to add UserData key 
        # info in body.additional_para_for_ns, so we need to handle this new case
        if (domain == "local" and body.additional_param_for_ns and ("nsId" not in body.additional_param_for_ns) and ("network_mapping" not in body.additional_param_for_ns) ):
            log_queue.put(["INFO", "SOEp delegating the INSTANTIATION to SOEc"])
            ps = Process(target=soe.instantiate_ns_process, args=(nsId, body))
            ps.start()
            # save process
            soe.processes[operationId] = ps
        else:
            log_queue.put(["INFO", "SOEp taking charge of the instantiation"])
            ps = Process(target=instantiate_ns_process, args=(nsId,body, request_origin))
            ps.start()
            # save process
            processes_parent[operationId] = ps
    # log_queue.put(["INFO", "*****Time measure: finished instantiation at SOEp"])
    return operationId


def scale_ns(nsId, body):
    """
    Starts a process to scale the Network Service associated with the instance identified by "nsId".
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    body: request body
    Returns
    -------
    string
        Id of the operation associated to the Network Service instantiation.
    """

    log_queue.put(["INFO", "scale_ns for nsId %s with body: %s" % (nsId, body)])

    if not ns_db.exists_nsId(nsId):
        return 404

    status = ns_db.get_ns_status(nsId)
    if status != "INSTANTIATED":
        return 400
    ns_db.set_ns_status(nsId, "SCALING")
    operationId = create_operation_identifier(nsId, "INSTANTIATION")
    # for the moment, we only consider two cases for scaling:  
    # 1) local scaling and 2) scaling of a single delegated NS
    # get the nsdId that corresponds to nsId
    nsdId = ns_db.get_nsdId(nsId)
    nsd_json = nsd_db.get_nsd_json(nsdId, None)
    domain = nsd_db.get_nsd_domain (nsdId)
    log_queue.put(["DEBUG", "scaling domain: %s"%(domain)])
    if (domain == "local"):
        log_queue.put(["DEBUG", "SOEp delegating the SCALING to SOEc"])
        ps = Process(target=soe.scale_ns_process, args=(nsId, body))
        ps.start()
        # save process
        soe.processes[operationId] = ps
    else:
        # soep should do things: there are nested, there is a reference, there is delegation
        if "nestedNsdId" in nsd_json["nsd"].keys():
            return 404
        else:
            log_queue.put(["DEBUG", "SOEp taking charge of the scaling"])
            ps = Process(target=scale_ns_process, args=(nsId,body))
            ps.start()
            # save process
            processes_parent[operationId] = ps

    return operationId


def terminate_ns(nsId, requester):
    """
    Starts a process to terminate the NS instance identified by "nsId".
    Parameters
    ----------
    nsId: string
        Identifier of the NS instance to terminate.
    requester: string
        IP address of the entity making the request
    Returns
    -------
    operationId: string
        Identifier of the operation in charge of terminating the service.
    """
    log_queue.put(["INFO", "*****Time measure: SOEp SOEp terminating a NS"])
    if not ns_db.exists_nsId(nsId):
        return 404
    registered_requester = ns_db.get_ns_requester(nsId)
    if (registered_requester != requester):
        return 404
    # check the ns status
    status = ns_db.get_ns_status(nsId)
    log_queue.put(["INFO", "Network service %s is in %s state." % (nsId, status)])

    if status in ["TERMINATING", "TERMINATED", "NOT_INSTANTIATED"]:
        return 400
    # if status is INSTANTIATING, kill the instantiation process
    if status == "INSTANTIATING":
        # set related operation as CANCELLED
        operationId = operation_db.get_operationId(nsId, "INSTANTIATION")
        operation_db.set_operation_status(operationId, "CANCELLED")
        # cancel instantiation process
        process = processes_parent[operationId]
        process.terminate()
        process.join()

    # we need to know if it is a single or a composite service, here we assume that everything is in INSTANTIATED state
    nsdId = ns_db.get_nsdId(nsId)
    domain = nsd_db.get_nsd_domain (nsdId)
    # first we create the operation Id to terminate the service, this will be the one that the 5GT-VS will poll
    operationId = create_operation_identifier(nsId, "TERMINATION")
    if (domain == "local"):
        # first check if it is possible to remove the service
        sharing_status = ns_db.get_sharing_status(nsId)
        if sharing_status:
            # this single NS is being used by a composite, so 5GT-SO will 
            # will not process the request
            return 400
        else:
            # this single NS is not being used by other composite/ 
            # or its relations have already finished
            log_queue.put(["INFO", "SOEp delegating the TERMINATION to SOEc"])
            ps = Process(target=soe.terminate_ns_process, args=(nsId, None))
            ps.start()
            soe.processes[operationId] = ps
    else: 
        log_queue.put(["DEBUG", "SOEp taking charge of the TERMINATION operation"])
        ps = Process(target=terminate_ns_process, args=(nsId, None))
        ps.start()
        # save process
        processes_parent[operationId] = ps
    # log_queue.put(["INFO", "*****Time measure: finished termination at SOEp"])
    return operationId


def query_ns(nsId):
    """
    Returns the information of the Network Service Instance identified by nsId.
    Parameters
    ----------
    nsId: string
        Identifier of the NS instance to terminate.
    Returns
    -------
    dict
        Information of the Network Service Instance.
    """

    if not ns_db.exists_nsId(nsId):
        # TODO create errors
        return 404
    # TODO: lines below are a stub
    status = ns_db.get_ns_status(nsId)
    vs_status = "FAILED"
    if status in [ "TERMINATED", "INSTANTIATING", "TERMINATING"]:
        vs_status = "NOT_INSTANTIATED"
    elif status == "INSTANTIATED":
        vs_status = "INSTANTIATED"

    nsd_id = ns_db.get_nsdId(nsId)
    domain = nsd_db.get_nsd_domain (nsd_id)
    nsd_json = nsd_db.get_nsd_json(nsd_id)
    info = {}
    if (domain == "local"):
        # single local NS
        info = soe.query_ns(nsId) 
    else:
        # two cases, it is composite or it is delegated 
        ns_name = ns_db.get_ns_name(nsId)
        ns_description = ns_db.get_ns_description(nsId)
        flavour_id = ns_db.get_ns_flavour_id(nsId)
        info = {"nsInstanceId":nsId,
                "nsName": ns_name,
                "description": ns_description,
                "nsdId": nsd_id,
                "flavourId": flavour_id,
                "nsState": vs_status,
             }
        ns_info_record = ns_db.get_nested_service_info(nsId) 
        aggregated_user_access_info = []   
        info["sapInfo"] = []
        if "nestedNsdId" in nsd_json["nsd"]:
            if vs_status == "NOT_INSTANTIATED":
                info["sapInfo"] = []
            else:
                # it is a composite so you need to construct the sap info result
                # first we make a mapping at crooe with the saps and the nsVirtuaLinkDesc
                log_queue.put(["DEBUG", "query_result for nsId: %s" % nsId])
                sap_composite_mapping  = crooe.mapping_composite_saps_to_nested_saps(nsId, nsd_json)
                log_queue.put(["DEBUG", "sap_composite_mapping: %s" % dumps(sap_composite_mapping, indent=4, sort_keys=True)])
                # sap_mapping: {'mgt_ehealth_mon_sap': {'eHealth-vEPC': ['mgt_vepc_sap'], 'eHealth-BE': ['mgt_ehealth_mon_be_sap']}}
                nested_info = ns_db.get_nested_service_info(nsId)
                # now treat the case of a reference
                reference_ns = ns_db.get_ns_nested_services_ids(nsId)
                for sap in sap_composite_mapping.keys():
                    sap_info = {}
                    sap_info["address"] = "test for future"
                    sap_info["description"] = sap_composite_mapping[sap]["info"]["description"]
                    sap_info["sapInstanceId"] = "0"
                    sap_info["sapName"] = sap_composite_mapping[sap]["info"]["cpdId"]
                    sap_info["sapdId" ] = sap_composite_mapping[sap]["info"]["cpdId"]
                    sap_info["userAccessInfo"] = []
                    for nested in nested_info:
                        if nested["nested_id"] in sap_composite_mapping[sap]["nested"].keys():
                            for sap2 in sap_composite_mapping[sap]["nested"][nested["nested_id"]]:
                                for sap3 in nested["sapInfo"]:
                                    if (sap2 == sap3["sapdId"]):
                                       sap_info["userAccessInfo"] = sap_info["userAccessInfo"] +sap3["userAccessInfo"] 
                    info["sapInfo"].append(sap_info)
                if reference_ns:
                    reference_ns = ns_db.get_ns_nested_services_ids(nsId)
                    reference_nsd_id = ns_db.get_nsdId(reference_ns)
                    reference_nsd_json = nsd_db.get_nsd_json(reference_nsd_id)
                    for sap in sap_composite_mapping.keys():
                        for sap2 in sap_composite_mapping[sap]["nested"].keys():
                            if sap2 == reference_nsd_json["nsd"]["nsdIdentifier"]:
                                if "sapd" in reference_nsd_json["nsd"]:
                                    sap_reference_info = get_ns_sap_info(reference_ns, reference_nsd_json["nsd"]["sapd"])
                                    log_queue.put(["DEBUG", "sap_reference_info: %s"% sap_reference_info])
                                    for sap3 in sap_reference_info:
                                        for sap4 in sap_composite_mapping[sap]["nested"][sap2]:
                                            if sap3["sapdId"] == sap4:
                                                for elem in info["sapInfo"]:
                                                    if elem["sapdId"] == sap:
                                                        elem["userAccessInfo"] = elem["userAccessInfo"] + sap3["userAccessInfo"]
        else:
            # it is a delegated one, so we get the info from our databases
            for nested_service in ns_info_record:
                if (nested_service["nested_id"] == nsd_id):
                    info["sapInfo"] = nested_service["sapInfo"]
    log_queue.put(["DEBUG", "query_result: %s"% dumps(info, indent=4, sort_keys=True)])
    return info

def get_ns_sap_info(nsi_id, nsd_saps):
    sap_list = []
    nsi_sap_info = ns_db.get_ns_sap_info(nsi_id)
    for current_sap in nsd_saps:
        if current_sap["cpdId"] in nsi_sap_info:
            sap_address = "test for future"
            user_access_info = []
            for address in nsi_sap_info[current_sap["cpdId"]]: 
                for key in address.keys():
                    user_info_dict = {}
                    user_info_dict['address'] = address[key]
                    user_info_dict['sapdId'] = current_sap["cpdId"]
                    user_info_dict['vnfdId'] = key
                    user_access_info.append(user_info_dict)
                new_sap = {"sapInstanceId": "0",
                           "sapdId": current_sap["cpdId"],
                           "sapName": current_sap["cpdId"],
                           "description": current_sap["description"],
                           "address": sap_address,
                           "userAccessInfo": user_access_info
                       }
            sap_list.append(new_sap)
    # log_queue.put(["INFO", "get_ns_sap_info output nsi_id:%s nsi_sap:%s" % (nsi_id, sap_list)])
    return sap_list

def get_operation_status(operationId):
    """
    Function to get the status of the operation identified by operationId.
    Parameters
    ----------
    operationId
        Identifier of the operation.
    Returns
    -------
    string
        status of the operation.
    """

    if not operation_db.exists_operationId(operationId):
        return 404

    status = operation_db.get_operation_status(operationId)

    return status


def query_nsd(nsdId, version):
    """
    Function to get the IFA014 json of the NSD defined by nsdId and version.
    Parameters
    ----------
    nsdId: string
        Identifier of the network service descriptor.
    version: string
        Version of the network service descriptor.

    Returns
    -------
    dict
        network service IFA014 json descriptor
    """
    nsd_json = nsd_db.get_nsd_json(nsdId, version)
    if nsd_json is None:
        return 404
    return nsd_json

def query_vnfd(vnfdId, version):
    """
    Function to get the IFA014 json of the VNFD defined by vnfdId and version.
    Parameters
    ----------
    vnfdId: string
        Identifier of the virtual network function descriptor.
    version: string
        Version of the virtual network function descriptor.

    Returns
    -------
    dict
        virtual network function IFA014 json descriptor
    """
    vnfd_json = vnfd_db.get_vnfd_json(vnfdId, version)
    if vnfd_json is None:
        return 404
    return vnfd_json

def query_appd(appdId, version):
    """
    Function to get the MEC010-2 json of the MEC app defined by appdId and version.
    Parameters
    ----------
    appdId: string
        Identifier of the MEC application descriptor.
    version: string
        Version of the MEC application descriptor.

    Returns
    -------
    dict
        MEC application MEC010-2 json descriptor
    """
    appd_json = appd_db.get_appd_json(appdId, version)
    if appd_json is None:
        return 404
    return appd_json

def delete_nsd(nsdId, version):
    """
    Function to delete from the catalog the NSD defined by nsdId and version.
    Parameters
    ----------
    nsdId: string
        Identifier of the network service descriptor.
    version: string
        Version of the network service descriptor.

    Returns
    -------
    boolean
    """
    operation_result = nsd_db.delete_nsd_json(nsdId, version)
    return operation_result

def delete_vnfd(vnfdId, version):
    """
    Function to delete from the catalog the VNFD defined by vnfdId and version.
    Parameters
    ----------
    vnfdId: string
        Identifier of the virtual network function descriptor.
    version: string
        Version of the virtual network function service descriptor.

    Returns
    -------
    boolean
    """
    operation_result = vnfd_db.delete_vnfd_json(vnfdId, version)
    return operation_result

def delete_appd(appdId, version):
    """
    Function to delete from the catalog the MEC app defined by vnfdId and version.
    Parameters
    ----------
    appdId: string
        Identifier of the MEC application descriptor.
    version: string
        Version of the MEC application descriptor.

    Returns
    -------
    boolean
    """
    operation_result = appd_db.delete_appd_json(appdId, version)
    return operation_result

def onboard_nsd(nsd_json, requester):
    """
    Function to onboard the NSD contained in the input.
    Parameters
    ----------
    nsd_json: dict
        IFA014 network service descriptor.
    requester: string
        IP address of the requester
    Returns
    -------
    nsdInfoId: string
        The identifier assigned in the db
    """
    log_queue.put(["INFO", "Requester Onboard_nsd: %s"% requester])
    domain = None
    shareable = "True"
    #if (requester == "127.0.0.1"):
    if (requester in available_VS):
        #assuming VS in the same machine
        domain = "local"
    else:
        for elem in fed_domain.keys():
            if (fed_domain[elem] == requester):
                #domain = elem
                domain = {elem: requester}
                shareable = "False" # for the moment, we are not going to consider the sharing with federated network services
    if ("nestedNsdId" in nsd_json["nsd"].keys()):
        # it is suppose that the nested ones will be available at the database
        domain = "Composite"
        shareable = "False" #composite network services cannot be shared by others

    if domain is not None:
        nsd_record = {"nsdId": nsd_json["nsd"]["nsdIdentifier"],
                      # "nsdCloudifyId": nsdCloudifyId["eHealth_v01"],
                      "version": nsd_json["nsd"]["version"],
                      "nsdName": nsd_json["nsd"]["nsdName"],
                      "nsdJson": nsd_json,
                      "domain": domain,
                      "shareable": shareable}
        log_queue.put(["DEBUG", "ONBOARD_NSD result: %s"% dumps(nsd_record, indent=4)])
        if nsd_db.exists_nsd(nsd_json["nsd"]["nsdIdentifier"], nsd_json["nsd"]["version"]):
            # it is an update, so remove previously the descriptor
            nsd_db.delete_nsd_json(nsd_json["nsd"]["nsdIdentifier"])
        # then insert it again (creation or "update")
        nsd_db.insert_nsd(nsd_record)
        if (domain == "local"):
            # this descriptor has to be uploaded in the MANO platform
            soe.onboard_nsd_mano(nsd_json)         
        return nsd_record["nsdId"]
    else:
        return 404

def onboard_vnfd(body):
    """
    Function to onboard the VNFD, including the downloading from the url specified in the input.
    Parameters
    ----------
    body: dict
        IFA013 request to onboard a vnfd.
    Returns
    -------
    info: dict
        Dictionary with the IFA013 answer to the vnfd onboarding process
    """
    log_queue.put(["INFO", "vnf_package_path: %s"% body.vnf_package_path])
    filename=wget.download(body.vnf_package_path)
    tf=tarfile.open(filename)
    tf.extractall()
    with tf as _tar:
        for member in _tar:
            if member.isdir():
                continue
            print (member.name)
            if member.name.find("json"):
                fname = member.name
                break
    # upload it in the vnfd_db 
    if (fname):         
         with open(fname) as vnfd_json:
             vnfd_json = load(vnfd_json)
             vnfd_record = {"vnfdId": vnfd_json["vnfdId"],
                            "vnfdVersion": vnfd_json["vnfdVersion"],
                            "vnfdName": vnfd_json["vnfProductName"],
                            "vnfdJson": vnfd_json}
         if vnfd_db.exists_vnfd(vnfd_json["vnfdId"], vnfd_json["vnfdVersion"]):
             vnfd_db.delete_vnfd_json(vnfd_json["vnfdId"])
         # then insert it again (creation or "update")
         vnfd_db.insert_vnfd(vnfd_record)
         # upload the descriptor in the MANO platform
         soe.onboard_vnfd_mano(vnfd_json)
         # create the answer
         info = {"onboardedVnfPkgInfoId": vnfd_record["vnfdId"],
                 "vnfId": vnfd_record["vnfdId"]}
    # remove the tar package and the json file
    os.remove(filename)
    os.remove(fname) 
    return info

def onboard_appd(body):
    """
    Function to onboard the APPD, including the downloading from the url specified in the input.
    Parameters
    ----------
    body: dict
        IFA013 request to onboard an appd.
    Returns
    -------
    info: dict
        Dictionary with the IFA013 answer to the appd onboarding process
    """
    log_queue.put(["INFO", "app_package_path: %s"% body.app_package_path])
    filename=wget.download(body.app_package_path)
    tf=tarfile.open(filename)
    tf.extractall()
    with tf as _tar:
        for member in _tar:
            if member.isdir():
                continue
            print (member.name)
            if member.name.find("json"):
                fname = member.name
                break
    # upload it in the vnfd_db 
    if (fname):         
         with open(fname) as appd_json:
             appd_json = load(appd_json)
             appd_record = {"appdId": appd_json["appDId"],
                            "appdVersion": appd_json["appDVersion"],
                            "appdName": appd_json["appName"],
                            "appdJson": appd_json}
         if appd_db.exists_appd(appd_json["appDId"], appd_json["appDVersion"]):
             appd_db.delete_appd_json(appd_json["appDId"])
         # then insert it again (creation or "update")
         appd_db.insert_appd(appd_record)
         # create the answer
         info = {"onboardedAppPkgId": appd_record["appdId"],
                 "appDId": appd_record["appdId"]}
    # remove the tar package and the json file
    os.remove(filename)
    os.remove(fname) 
    return info


