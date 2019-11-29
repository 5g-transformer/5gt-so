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
import os
import tarfile
from uuid import uuid4
from multiprocessing import Process, Queue

import wget
from pymongo import MongoClient
from json import dumps, loads, load
import sys
import copy
import time
import wget
import tarfile
import os

# project imports
from db.ns_db import ns_db
from db.nsd_db import nsd_db
from db.vnfd_db import vnfd_db
from db.appd_db import appd_db
from db.operation_db import operation_db
from sm.rooe import rooe
from nbi import log_queue
from monitoring import monitoring, alert_configure

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


def instantiate_ns_process(nsId, body, nestedInfo=None):
    """
    Function description
    Parameters
    ----------
    nsId: string
        Identifier of the service
    body: struct
        Object having the deployment flavour and the instantiation level.
    nsdIdc: string
        Identifier of the nested service to be instantiated, only available when composing
    Returns
    -------
    name: type
        return description
    """
    log_queue.put(["INFO", "*****Time measure: SOEc SOEc instantiating a NS"])
    log_queue.put(["INFO", "SOEc instantiate_ns_process with nsId %s, body %s" % (nsId, body)])
    # get the nsdId that corresponds to nsId
    nsdId = ns_db.get_nsdId(nsId)
    if nestedInfo:
        nsdId = next(iter(nestedInfo))
    # first get the ns and vnfs descriptors
    nsd_json = nsd_db.get_nsd_json(nsdId, None)
    vnfds_json = {}
    # for each vnf in the NSD, get its json descriptor
    vnfdIds = nsd_json["nsd"]["vnfdId"]
    vnfds_json = {}
    for vnfdId in vnfdIds:
        log_queue.put(["DEBUG", vnfdId])
        vnfds_json[vnfdId] = vnfd_db.get_vnfd_json(vnfdId, None)
    # request RO
    rooe.instantiate_ns(nsId, nsd_json, vnfds_json, body, nestedInfo)
    log_queue.put(["INFO", "*****Time measure: SOEc updated databases instantiating"])
    sap_info = ns_db.get_ns_sap_info(nsId)
    if (len(sap_info) > 0):
      log_queue.put(["INFO", "sapInfo: %s"% (sap_info)])
      monitoring.configure_ns_monitoring(nsId, nsd_json, vnfds_json, sap_info)
      log_queue.put(["INFO", "instantiate_ns monitoring exporters created for nsId %s" % (nsId)])
      # initiate alerts
      alert_configure.configure_ns_alerts(nsId, nsdId, nsd_json, vnfds_json, sap_info)
      log_queue.put(["INFO", "*****Time measure: SOEc created monitoring exporters and alerts"]) 
    log_queue.put(["INFO", "*****Time measure: SOEc instantiate_ns_process finished for nsId %s" % (nsId)])

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
    log_queue.put(["INFO", "scale_ns_process with nsId %s, body %s" % (nsId, body)])
    # get the nsdId that corresponds to nsId
    nsdId = ns_db.get_nsdId(nsId)
    # get current instantiation level
    current_df = ns_db.get_ns_df(nsId)
    current_il = ns_db.get_ns_il(nsId)
    # first get the ns and vnfs descriptors
    nsd_json = nsd_db.get_nsd_json(nsdId, None)
    # for each vnf in the NSD, get its json descriptor
    vnfdIds = nsd_json["nsd"]["vnfdId"]
    vnfds_json = {}
    for vnfdId in vnfdIds:
        vnfds_json[vnfdId] = vnfd_db.get_vnfd_json(vnfdId, None)
    #request RO
    sap_info_pre_scaling = ns_db.get_ns_sap_info(nsId)
    rooe.scale_ns(nsId, nsd_json, vnfds_json, body, current_df, current_il)
    # maybe we have to update the monitoring jobs: we assume that new performance monitoring jobs
    # will be similar to one already present
    sap_info = ns_db.get_ns_sap_info(nsId)
    log_queue.put(["INFO", "new sapInfo after scaling: %s"% (sap_info)])
    monitoring.update_ns_monitoring(nsId, nsd_json, vnfds_json, sap_info)
    log_queue.put(["DEBUG", "monitoring exporters updated after scaling for nsId %s" % (nsId)])
    # update alerts: it is not needed
    log_queue.put(["INFO", "scale_ns_process finished for nsId %s" % (nsId)])



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
    #first terminate the alert/monitoring jobs
    # When alert rest API will be ready uncomment
    log_queue.put(["INFO", "SOEc eliminating service with nsId: %s"%nsId])
    if (nsId.find("_") == -1):
        # terminate alerts
        alert_configure.delete_ns_alerts(nsId)
        # terminate monitoring jobs
        monitoring.stop_ns_monitoring(nsId)
        log_queue.put(["INFO", "*****Time measure: SOEc terminated monitoring exporters and alerts"])
    #terminate the service
    rooe.terminate_ns(nsId)
    log_queue.put(["INFO", "*****Time measure: SOEc updated databases terminating"])
    ns_db.delete_ns_record(nsId)

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
    Returns
    -------
    string
        Id of the operation associated to the Network Service instantiation.
    """
    log_queue.put(["INFO", "*****Time measure: SOEc SOEc instantiating a nested"])
    log_queue.put(["INFO", "instantiate_ns for nsId %s with body: %s" % (nsId, body)])
    #client = MongoClient()
    #fgtso_db = client.fgtso
    #ns_coll = fgtso_db.ns

    if not ns_db.exists_nsId(nsId):
        return 404

    status = ns_db.get_ns_status(nsId)
    if status != "NOT_INSTANTIATED":
        return 400
    ns_db.save_instantiation_info(nsId, body, requester)

    operationId = create_operation_identifier(nsId, "INSTANTIATION")
    ps = Process(target=instantiate_ns_process, args=(nsId, body))
    ps.start()

    # save process
    processes[operationId] = ps
    # log_queue.put(["INFO", "*****Time measure: SOEc finished instantiation at SOEc"])
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
    # client = MongoClient()
    # fgtso_db = client.fgtso
    # ns_coll = fgtso_db.ns

    if not ns_db.exists_nsId(nsId):
        return 404

    status = ns_db.get_ns_status(nsId)
    if status != "INSTANTIATED":
        return 400
    ns_db.set_ns_status(nsId, "SCALING")
    operationId = create_operation_identifier(nsId, "INSTANTIATION")
    ps = Process(target=scale_ns_process, args=(nsId, body))
    ps.start()

    # save process
    processes[operationId] = ps

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
    log_queue.put(["INFO", "*****Time measure: SOEc SOEc terminating a nested"])
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
        process = processes[operationId]
        process.terminate()
        process.join()

    operationId = create_operation_identifier(nsId, "TERMINATION")
    ps = Process(target=terminate_ns_process, args=(nsId, None))
    ps.start()

    # save process
    processes[operationId] = ps
    # log_queue.put(["INFO", "*****Time measure: finished termination at SOEc"])
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
    nsd_json = nsd_db.get_nsd_json(nsd_id)
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
    if "sapd" in nsd_json["nsd"]:
        total_sap_info = get_ns_sap_info(nsId,nsd_json["nsd"]["sapd"])
        if total_sap_info is not None:
            info["sapInfo"] = total_sap_info
    
    dashboard_info = ns_db.get_dashboard_info(nsId)
    if "dashboardUrl" in dashboard_info.keys():
        info["monitoringDashboardUrl"] = dashboard_info["dashboardUrl"]

    log_queue.put(["INFO", "query_result: %s"% dumps(info, indent=4, sort_keys=True)])
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
                    #user_info_dict = {'address':'','sapdId': '', 'vnfdId':''}
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
    log_queue.put(["DEBUG", "Requester Onboard_nsd: %s"% requester])
    nsd_record = {"nsdId": nsd_json["nsd"]["nsdIdentifier"],
                  # "nsdCloudifyId": nsdCloudifyId["eHealth_v01"],
                  "version": nsd_json["nsd"]["version"],
                  "nsdName": nsd_json["nsd"]["nsdName"],
                  "nsdJson": nsd_json}
    if nsd_db.exists_nsd(nsd_json["nsd"]["nsdIdentifier"], nsd_json["nsd"]["version"]):
        # it is an update, so remove previously the descriptor
        nsd_db.delete_nsd_json(nsd_json["nsd"]["nsdIdentifier"])
    # then insert it again (creation or "update")    
    nsd_db.insert_nsd(nsd_record)
    # upload the descriptor in the MANO platform
    onboard_nsd_mano(nsd_json) 
    return nsd_record["nsdId"]

def onboard_nsd_mano(nsd_json):
    """
    Function which calls the ROOE to create a wrapper to onboardd the NSD contained in the input
    at the corresponding MANO platform.
    Parameters
    ----------
    nsd_json: dict
        IFA014 network service descriptor.
    Returns
    -------
    None
    """
    rooe.onboard_nsd_mano(nsd_json)

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
         onboard_vnfd_mano(vnfd_json) 
         # create the answer
         info = {"onboardedVnfPkgInfoId": vnfd_record["vnfdId"],
                 "vnfId": vnfd_record["vnfdId"]}
    # remove the tar package and the json file
    os.remove(fname) 
    return info

def onboard_vnfd_mano(vnfd_json):
    """
    Function which calls the ROOE to create a wrapper to onboardd the NSD contained in the input
    at the corresponding MANO platform.
    Parameters
    ----------
    vnfd_json: dict
        IFA011 virtual network function descriptor.
    Returns
    -------
    None
    """
    rooe.onboard_vnfd_mano(vnfd_json)

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
