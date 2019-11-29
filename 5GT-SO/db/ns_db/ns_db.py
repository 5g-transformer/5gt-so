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
Database of Network Service Instances
DB structure:
    nsId: string
    status: string  (one of: NOT_INSTANTIATED, INSTANTIATING, INSTANTIATED, TERMINATING, TERMINATED)
    nsdId: string
    nsDescription: string
    nsName: string
    flavourId: string,
    nsInstantiationLevelId: string
"""
# python imports
from json import dumps, loads, load

# mongodb imports
from bson import ObjectId
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
ns_client = MongoClient(db_ip, db_port)
fgtso_db = ns_client.fgtso

# create network service instances collection
ns_coll = fgtso_db.ns


####### SO methods
# network service instances collection functions
def create_ns_record(nsId, body):
    """
    Creates an entry in the ns_coll with
    Parameters
    ----------
    nsId: string
        Id of the Network Service Instance
    body: Request Body
        body received by the
    Returns
    -------
    None
    """
    ns_record = {"nsId": nsId,
                 "status": "NOT_INSTANTIATED",
                 "nsd_id": body.nsd_id,
                 "ns_name": body.ns_name,
                 "ns_description": body.ns_description,
                 "sapInfo": "",
                 "monitoring_jobs": [],
                 "dashboard_info": {},
                 }

    ns_coll.insert_one(ns_record)


def save_instantiation_info(nsId, body, requester):
    """
    Save in ns_coll the information received in the body of the ns instantiation request.
    Also sets the status to "INSTANTIATING"
    ----------
    nsId: string
        Id of the Network Service Instance
    body: Request Body
        body received by the NBI
    requester: string
        IP address of the requester entity
    Returns
    -------
    None
    """
    if body.additional_param_for_ns:
        if "network_mapping" in body.additional_param_for_ns:
            # This means that the request is a nested from a federated one
            nestedRequest = loads(body.additional_param_for_ns["network_mapping"]) #this is a list
            ns_coll.update_one({"nsId": nsId}, {"$set": {"status": "INSTANTIATING",
                                                         "flavourId": body.flavour_id,
                                                         "nsInstantiationLevelId": body.ns_instantiation_level_id,
                                                         "requester": requester,
                                                         "federatedInfo": nestedRequest}})
        else:
            ns_coll.update_one({"nsId": nsId}, {"$set": {"status": "INSTANTIATING",
                                                         "flavourId": body.flavour_id,
                                                         "nsInstantiationLevelId": body.ns_instantiation_level_id,
                                                         "requester": requester}})

    else:
        ns_coll.update_one({"nsId": nsId}, {"$set": {"status": "INSTANTIATING",
                                                     "flavourId": body.flavour_id,
                                                     "nsInstantiationLevelId": body.ns_instantiation_level_id,
                                                     "requester": requester}})


def get_ns_federation_info(nsId):
    """
    Function to get the federation info of a nested Network Service Instance
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    dict
        Federation info of the Network Service Instance consisting of the consumer nsId and the 
        network mapping of internested connections
    """
    ns = ns_coll.find_one({"nsId": nsId})
    return ns["federatedInfo"]

def get_ns_requester(nsId):
    """
    Function to get the federation info of a nested Network Service Instance
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    requester: string
        IP address of the requester entity
    """
    ns = ns_coll.find_one({"nsId": nsId})
    return ns["requester"]

def set_ns_nested_services_ids(nsId, nested_nsId):
    """
    Save in ns_coll the information received in nested_nsId, that is, 
    for a composite network service, we save the nested id if there is.
    ----------
    nsId: string
        Id of the COMPOSITE Network Service Instance
    nested_nsId: string
        Id received in the instantiation request
    Returns
    -------
    None
    """
    # we set it directly, because a composite can only use another nested
    ns_coll.update_one({"nsId": nsId}, {"$set": {"nestedNsId": nested_nsId}})

def get_ns_nested_services_ids(nsId):
    """
    Save in ns_coll the information received in nested_nsId, that is, 
    for a composite network service, we save the nested id if there is.
    ----------
    nsId: string
        Id of the COMPOSITE Network Service Instance
    Returns 
    nested_nsId: string
        Id of the reference use to instantiate the COMPOSITE Network Service
    """
    ns = ns_coll.find_one({"nsId": nsId})
    if "nestedNsId" in ns:
        return ns["nestedNsId"]
    else:
        return None

def delete_ns_nested_services_ids(nsId):
    """
    Delete in ns_coll the information of links with other nested services
    ----------
    nsId: string
        Id of the COMPOSITE Network Service Instance
    Returns
    -------
    nested_nsId: string
    Id received in the instantiation request
    """
    ns = ns_coll.find_one({"nsId": nsId})
    nestedNsId = ns["nestedNsId"]
    # we set it to void, because this will be invoked when terminated and this registry removed
    ns_coll.update_one({"nsId": nsId}, {"$set": {"nestedNsId": ""}})
    return nestedNsId

def set_ns_shared_services_ids(nsId_owner, nsId_child):
    """
    Save in ns_coll the information received in nsId_child, that is, we save in
    the "owner service" (the original one) the id of the composite one using it.
    ----------
    nsId_owner: string
        the original instantiated service which is used to instantiate a composite
    nsId_child: string
        Id of the composite network service. A owner service cannot be terminated
        if there is composite services associated to him
    Returns
    -------
    None
    """
    ns = ns_coll.find_one({"nsId": nsId_owner})
    used_by =  []
    used_by.append(nsId_child)
    if "used_by" in ns:
        used_by = ns["used_by"] + used_by
    ns_coll.update_one({"nsId": nsId_owner}, {"$set": {"used_by": used_by}})

def delete_ns_shared_services_ids(nsId_owner, nsId_child):
    """
    Delete in ns_coll the information received in nsId_child, that is, we remove in
    the "owner service" (the original one) the id of the composite one that has been deleted.
    ----------
    nsId_owner: string
        the original instantiated service which is used to instantiate a composite
    nsId_child: string
        Id of the composite network service. A owner service cannot be terminated
        if there is composite services associated to him
    Returns
    -------
    None
    """
    ns = ns_coll.find_one({"nsId": nsId_owner})
    if "used_by" in ns:
        new_used_by = []
        for index in range(0, len(ns["used_by"])):
            if (ns["used_by"][index] != nsId_child):
                new_used_by.append(ns["used_by"][index])
    ns_coll.update_one({"nsId": nsId_owner}, {"$set": {"used_by": new_used_by}})

def save_sap_info(nsId, sapInfo):
    """
    Save in ns_coll the information received for the SAPs during the instantiation.
    ----------
    nsId: string
        Id of the Network Service Instance
    sapInfo: Request Body
        sapInfo received from the nfvo
    Returns
    -------
    None
    """
    if (nsId.find('_') == -1):
        # this is a case of a single local nsd instance
        ns_coll.update_one({"nsId": nsId}, {"$set": {"sapInfo": sapInfo}})
    else:
        # this is the case of nested local nsd instance
        [nsId_global, nsd_name] = nsId.split('_')
        ns_coll.update_one({"nsId": nsId_global}, {"$set": {"sapInfo": sapInfo}})

def exists_nsId(nsId):
    """
    Function to check if an NS instance with identifier "nsId" exists.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    boolean
        returns True if a NS instance with Id "nsId" exists in "ns_coll". Returns False otherwise.
    """
    ns = ns_coll.find_one({"nsId": nsId})
    if ns is None:
        return False
    return True

def get_sharing_status(nsId):
    """
    Function to check if the service is used by other service (a composite one)
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    bool
        True if it is being used, false otherwise.
    """
    ns_record = get_ns_record(nsId)
    if "used_by" in ns_record:
        if len(ns_record["used_by"]) > 0:
            return True
        else:
            return False
    else:
        return False

def get_ns_status(nsId):
    """
    Function to get the status of a Network Service Instance
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    string
        Status of the Network Service Instance.
    """
    ns = ns_coll.find_one({"nsId": nsId})
    return ns["status"]

def get_ns_record(nsId):
    """
       Function to get the record of a Network Service Instance
       Parameters
       ----------
       nsId: string
           Identifier of the Network Service Instance.
       Returns
       -------
       dict
           ns record of the Network Service Instance.
       """
    ns = ns_coll.find_one({"nsId": nsId})
    return ns

def set_ns_status(nsId, status):
    """
    Function to set the status of a Network Service Instance
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    """
    ns_coll.update_one({"nsId": nsId}, {"$set": {"status": status}})

def get_ns_il(nsId):
    """
    Function to get the instantiationLevel of a Network Service Instance
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    string
        Instantiation Level of the Network Service Instance.
    """
    ns = ns_coll.find_one({"nsId": nsId})
    return ns["nsInstantiationLevelId"]

def set_ns_il(nsId, instantiation_level):
    """
    Function to get the instantiationLevel of a Network Service Instance
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    target_il: string
        Instantiation level of the Network Service Instance.
    Returns
    -------
    None
    """
    ns_coll.update_one({"nsId": nsId}, {"$set": {"nsInstantiationLevelId": instantiation_level}})

def get_ns_df(nsId):
    """
    Function to get the deployment flavour of a Network Service Instance
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    string
        Deployment flavour of the Network Service Instance.
    """
    ns = ns_coll.find_one({"nsId": nsId})
    return ns["flavourId"]

def get_ns_name(nsId):
    """
       Function to get the name of a Network Service Instance
       Parameters
       ----------
       nsId: string
           Identifier of the Network Service Instance.
       Returns
       -------
       string
           name of the Network Service Instance.
       """
    ns = ns_coll.find_one({"nsId": nsId})
    return ns["ns_name"]


def get_ns_description(nsId):
    """
    Function to get the description of a Network Service Instance
    Parameters
   ----------
   nsId: string
       Identifier of the Network Service Instance.
   Returns
   -------
   string
       name of the Network Service Instance.
   """
    ns = ns_coll.find_one({"nsId": nsId})
    return ns["ns_description"]


def get_ns_flavour_id(nsId):
    """
       Function to get the flavour id of a Network Service Instance
       Parameters
      ----------
      nsId: string
          Identifier of the Network Service Instance.
      Returns
      -------
      string
          flavour id of the Network Service Instance.
      """
    ns = ns_coll.find_one({"nsId": nsId})
    return ns["flavourId"]


def get_ns_sap_info(nsId):
    """
    Function to get the status of a Network Service Instance
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    string
        Status of the Network Service Instance.
    """
    ns = ns_coll.find_one({"nsId": nsId})
    if ns is not None and "sapInfo" in ns:
        return ns["sapInfo"]
    else:
        return None


def set_ns_status(nsId, status):
    """
    Function to set the status of a Network Service Instance
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    None
    """
    ns_coll.update_one({"nsId": nsId}, {"$set": {"status": status}})


def get_nsdId(nsId):
    """
    Function to get the Network Service Descriptor of the Network Service identified by nsId.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    string
        Identifier of the Network Service Descriptor.

    """
    ns = ns_coll.find_one({"nsId": nsId})
    if ns is None:
        return None
    return ns["nsd_id"]


def set_monitoring_info(nsId, info):
    """
    Adds the list of monitoring jobs for this NS instance.
    ----------
    nsId: string
        Reference to the appropriate nsId
    info: list
        List of monitoring jobs identifiers
    Returns
    -------
    None
    """
    ns_coll.update_one({"nsId": nsId}, {"$set": {"monitoring_jobs": info}})

def set_nested_service_info(nsId):
    """
    Creates the entry to store information related to nested services 
    ----------
    nsId: string
         Reference to the appropriate nsId
    Returns
    ---------
    None
    """
    ns_coll.update_one({"nsId": nsId}, {"$set": {"nested_service_info": []}})

def update_monitoring_info(nsId, info, old_info):
    """
    Updates the list of monitoring jobs for this NS instance.
    ----------
    info: list
        List of monitoring jobs dicts
    old_info: list
        List of monitoring jobs to be removed from db
    Returns
    -------
    None
    """
    pm_jobs = get_monitoring_info(nsId)
    # first, remove the ones that are not needed
    for index_a in range(0,len(pm_jobs)):
        for index_b in range (0, len(old_info)):
            if (pm_jobs[index_a]['exporterId'] == old_info[index_b]):
                deleted_pm_jobs = pm_jobs.pop(index_a)  
    # second, update the monitoring info
    pm_jobs = pm_jobs + info
    set_monitoring_info(nsId, pm_jobs)

def update_nested_service_info(nsId, info, operation, nestedId=None):
    """
    updates the information with respect to Adds the list of monitoring jobs ids for this NS instance.
    ----------
    nsId: string
        Reference to the appropriate nsId
    info: dict
        info about federated service instance
    operation: string
        info about the operation: push or set
    Returns
    -------
    None
    """
    if (operation == "set"):
        ns = ns_coll.find_one({"nsId": nsId})
        if nestedId:
            #I have to update one dictionary with new information
            for elem in ns["nested_service_info"]:
                if (elem["nested_instance_id"] == nestedId):
                    # first update the corresponding element
                    elem.update(info)
                    # second update all the information block
                    ns_coll.update_one({"nsId": nsId}, {"$set": {"nested_service_info": ns["nested_service_info"]}})
    if (operation == "push"):
        ns_coll.update_one({"nsId": nsId}, {"$push": {"nested_service_info": info}})

def get_nested_service_info(nsId):
    """
       Function to get the flavour id of a Network Service Instance
       Parameters
      ----------
      nsId: string
          Identifier of the Network Service Instance.
      Returns
      -------
      dict
          information related with each of the instantiated nested services.
      """
    ns = ns_coll.find_one({"nsId": nsId})
    if "nested_service_info" in ns:
        return ns["nested_service_info"]
    else:
        return []

def set_alert_info(nsId, info):
    """
    Adds the list of alerts ids for this NS instance.
    ----------
    info: list
        List of monitoring jobs identifiers
    Returns
    -------
    None
    """
    ns_coll.update_one({"nsId": nsId}, {"$set": {"alert_jobs": info}})


def get_monitoring_info(nsId):
    """
    Returns the list of monitoring jobs ids of this NS instance.
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    List 
        List of strings containing the monitoring ids associated to the nsId.
    """
    ns = ns_coll.find_one({"nsId": nsId})
    if "monitoring_jobs" in ns: 
        return ns["monitoring_jobs"]
    else:
        return []

def get_alerts_info(nsId):
    """
    Returns the list of alerts ids of this NS instance.
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    List
        List of strings containing the monitoring ids associated to the nsId.
    """
    ns = ns_coll.find_one({"nsId": nsId})
    if "alert_jobs" in ns:
        return ns["alert_jobs"]
    else:
        return {}

def set_dashboard_info(nsId, info):
    """
    Adds the id of the dashboard associated to this NS instance.
    ----------
    info: Dictionary
        Dictionary with dashboard info ("dashboardId" and "dashboardUrl" as keys) associated to the Network service
    Returns
    -------
    None
    """
    ns_coll.update_one({"nsId": nsId}, {"$set": {"dashboard_info": info}})


def get_dashboard_info(nsId):
    """
    Returns the id of the dashboard associated to this NS instance.
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    String
        Id of the dashboard associated to the nsId.
    """
    ns = ns_coll.find_one({"nsId": nsId})
    if "dashboard_info" in ns:
        return ns["dashboard_info"]
    else:
        return {}

def delete_ns_record(nsId):
    """
    deletes one element of the ns_coll
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    ns_coll.delete_one({"nsId":nsId}) 


def empty_ns_collection():
    """
    deletes all documents in the ns_coll
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    ns_coll.delete_many({})


####### GUI methods
def get_all_ns():
    """
    Returns all the NSs in che collection
    Parameters
    ----------
    Returns
    -------
    list of dict
    """
    return list(ns_coll.find())


def remove_ns_by_id(id):
    """
    Remove a NS from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of NS
    Returns
    -------
    dict
    """
    output = ns_coll.remove({"_id": ObjectId(id)})


def update_ns(id, body):
    """
    Update a NS from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of NS
    body: body to update
    Returns
    -------
    ???
    """
    output = ns_coll.update({"_id": ObjectId(id)}, {"$set": body})
    return output


def get_ns_instantiation_level_id(nsId):
    """
       Function to get the ns instantiation level id of a Network Service Instance
       Parameters
      ----------
      nsId: string
          Identifier of the Network Service Instance.
      Returns
      -------
      string
          ns instantiation level id of the Network Service Instance.
      """
    ns = ns_coll.find_one({"nsId": nsId})
    return ns["nsInstantiationLevelId"]
