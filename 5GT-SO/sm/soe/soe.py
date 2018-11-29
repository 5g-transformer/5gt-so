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
This file implements the Service Orchestration Engine.
"""

# python imports
from uuid import uuid4
from multiprocessing import Process, Queue
from pymongo import MongoClient
from json import dumps
from json import loads


# project imports
from db.ns_db import ns_db
from db.nsd_db import nsd_db
from db.vnfd_db import vnfd_db
from db.operation_db import operation_db
from sm.rooe import rooe
from nbi import log_queue

# dict to save processes by its nsId
processes = {}


########################################################################################################################
# PRIVATE METHODS                                                                                                      #
########################################################################################################################


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


def instantiate_ns_process(nsId, body):
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
    log_queue.put(["DEBUG", "instantiate_ns_process with nsId %s, body %s" % (nsId, body)])
    # get the nsdId that corresponds to nsId
    nsdId = ns_db.get_nsdId(nsId)
    # first get the ns and vnfs descriptors
    nsd_json = nsd_db.get_nsd_json(nsdId, "0.2")
    log_queue.put(["DEBUG", "instantiate_ns_process with nsId %s, body %s" % (nsId, body)])
    log_queue.put(["DEBUG", "NSD:"])
    log_queue.put(["DEBUG", dumps(nsd_json, indent=4)])
    vnfds_json = {}
    # for each vnf in the NSD, get its json descriptor
    vnfdIds = nsd_json["nsd"]["vnfdId"]
    vnfds_json = {}
    for vnfdId in vnfdIds:
        log_queue.put(["DEBUG", vnfdId])
        vnfds_json[vnfdId] = vnfd_db.get_vnfd_json(vnfdId, None)
    log_queue.put(["DEBUG", "VNFDs:"])
    log_queue.put(["DEBUG", dumps(vnfds_json, indent=4)])
    # request RO
    rooe.instantiate_ns(nsId, nsd_json, vnfds_json, body)


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
    rooe.terminate_ns(nsId)


def get_ns_sap_info(nsi_id, nsd_saps):
    log_queue.put(["DEBUG", "get_ns_sap_info nsi_id:%s nsd_sap:%s" % (nsi_id, nsd_saps)])
    sap_list = []
    nsi_sap_info = ns_db.get_ns_sap_info(nsi_id)
    if nsi_sap_info is None:
        return None
    log_queue.put(["DEBUG", "get_ns_sap_info nsi_id:%s nsi_sap:%s" % (nsi_id, nsi_sap_info)])
    for current_sap in nsd_saps:
        if current_sap["cpdId"] in nsi_sap_info:
            sap_address = nsi_sap_info[current_sap["cpdId"]]
            user_access_info = {
                "sapdId": current_sap["cpdId"],
                "address": sap_address
            }

            new_sap = {"sapInstanceId": "0",
                       "sapdId": current_sap["cpdId"],
                       "sapName": current_sap["cpdId"],
                       "description": current_sap["description"],
                       "address": sap_address,
                       "userAccessInfo": [user_access_info]

                       }
            sap_list.append(new_sap)
    log_queue.put(["DEBUG", "get_ns_sap_info output nsi_id:%s nsi_sap:%s" % (nsi_id, sap_list)])
    return sap_list


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
    # save to DB
    ns_db.create_ns_record(nsId, body)

    return nsId


def instantiate_ns(nsId, body):
    """
    Starts a process to instantiate the Network Service associated ti the instance identified by "nsId".
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

    log_queue.put(["INFO", "instantiate_ns for nsId %s with body: %s" % (nsId, body)])
    client = MongoClient()
    fgtso_db = client.fgtso
    ns_coll = fgtso_db.ns

    if not ns_db.exists_nsId(nsId):
        return 404

    status = ns_db.get_ns_status(nsId)
    if status != "NOT_INSTANTIATED":
        return 400
    ns_db.save_instantiation_info(nsId, body)

    operationId = create_operation_identifier(nsId, "INSTANTIATION")
    ps = Process(target=instantiate_ns_process, args=(nsId, body))
    ps.start()

    # save process
    processes[operationId] = ps

    return operationId


def terminate_ns(nsId):
    """
    Starts a process to terminate the NS instance identified by "nsId".
    Parameters
    ----------
    nsId: string
        Identifier of the NS instance to terminate.
    Returns
    -------
    operationId: string
        Identifier of the operation in charge of terminating the service.
    """

    if not ns_db.exists_nsId(nsId):
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
        process = processes[operationId]
        process.terminate()
        process.join()

    operationId = create_operation_identifier(nsId, "TERMINATION")
    ps = Process(target=terminate_ns_process, args=(nsId, None))
    ps.start()

    # save process
    processes[operationId] = ps

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
        return 404

    status = ns_db.get_ns_status(nsId)
    nsd_id = ns_db.get_nsdId(nsId)
    nsd_json = nsd_db.get_nsd_json(nsd_id)
    ns_name = ns_db.get_ns_name(nsId)
    ns_description = ns_db.get_ns_description(nsId)
    flavour_id = ns_db.get_ns_flavour_id(nsId)
    info = {"nsInstanceId": nsId,
            "nsName": ns_name,
            "description": ns_description,
            "nsdId": nsd_id,
            "flavourId": flavour_id,
            "nsState": status,
            }
    if "sapd" in nsd_json["nsd"]:
        info["sapInfo"] = get_ns_sap_info(nsId, nsd_json["nsd"]["sapd"])

    query_result = {"queryNsResult": [info]}
    log_queue.put(["DEBUG", "query_result: %s" % dumps(query_result, indent=4, sort_keys=True)])
    return query_result


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
