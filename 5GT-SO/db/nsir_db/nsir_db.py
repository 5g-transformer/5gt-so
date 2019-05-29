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
Database of resources used by Network Service Instances.
DB structure:
    nsId: string
    placement_info: dict
"""

# mongodb imports
from bson import ObjectId
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
nsir_client = MongoClient(db_ip, db_port)
fgtso_db = nsir_client.fgtso

# create nsir collection
nsir_coll = fgtso_db.nsir


####### SO methods
# network service instance resources collection functions
def exists_nsir(nsId):
    """
    Function to check if resources have been assigned to a Network Service Instance.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    boolean
        returns True if a NSI with Id "nsId" exists. Returns False otherwise.
    """
    nsir = nsir_coll.find_one({"nsId": nsId})
    if nsir is None:
        return False
    return True


def save_placement_info(nsId, placement_info):
    """
    Function to save the resources assigned to a Network Service Instance by the Placement Algorithm.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    placement info: dict
        Resources assigned to a Network Service Instance by the Placement Algorithm.
    Returns
    -------
    None
    """
    nsir_record = {"nsId": nsId,
                   "placement_info": placement_info,
                   "vl_list": None
                   }

    nsir_coll.insert_one(nsir_record)


def save_vim_networks_info(nsId, vim_net_info):
    """
    Function to save the created networks at vims to implement the VLs of a Network Service Instance .
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    vim_net_info: dict
        Information related to the networks created in the differents VIMs to implements the VLs of a Network Service Instance.
    Returns
    -------
    None
    """
    nsir_coll.update_one({"nsId": nsId}, {"$set": {"vim_net_info": vim_net_info}})


def save_vnf_deployed_info(nsId, vnf_deployed_info):
    """
    Function to save the information of instantiated VNFs to implement the VLs of a Network Service Instance .
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    vnf_deployed_info: dict
        Information related to the VNFs created in the differents VIMs.
    Returns
    -------
    None
    """
    nsir_coll.update_one({"nsId": nsId}, {"$set": {"vnf_info": vnf_deployed_info}})


def get_placement_info(nsId):
    """
    Function to get the resources assigned to a Network Service Instance by the Placement Algorithm.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.

    Returns
    -------
    placement info: dict
        Resources assigned by the Placement Algorithm to the Network Service Instance identified by nsId.
    """
    nsir = nsir_coll.find_one({"nsId": nsId})
    if "placement_info" in nsir:
        return nsir["placement_info"]
    else:
        return {}


def get_vim_networks_info(nsId):
    """
    Function to get the info of created networks at vim to support the VLs of the Network Service Instance as a result of the PA.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.

    Returns
    -------
    vim network info: dict
        Information related to the networks created in the differents VIMs to implements the VLs of a Network Service Instance.
    """
    nsir = nsir_coll.find_one({"nsId": nsId})

    return nsir["vim_net_info"]

def get_vnf_deployed_info(nsId):
    """
    Function to get the info of created networks at vim to support the VLs of the Network Service Instance as a result of the PA.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.

    Returns
    -------
    vnf_info: dict
        Information related to the vnfs created in the differents VIMs.
    """
    nsir = nsir_coll.find_one({"nsId": nsId})

    return nsir["vnf_info"]


def save_vls(vl_list, nsId):
    """
    Function save information of the virtual links deployed for a Network Service Instance.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    vl_list: list
        list of deployed virtual links
    Returns
    -------
    None
    """
    # in the case of composition/federation, vls are stored but the records 
    # has not been previously, created, so it is verified if the record exists 
    if exists_nsir (nsId):
        nsir_coll.update_one({"nsId": nsId}, {"$set": {"vl_list": vl_list}})
    else: 
        nsir_record = {"nsId": nsId,
                       "vl_list": vl_list
                      }
        nsir_coll.insert_one(nsir_record)
    
def set_network_mapping(mapping, nsId):
    """
    Function save information of network mapping for a composite Network Service Instance.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    mapping: dict
        dictionary with information extracted from CROOE module related to internested connections
    Returns
    -------
    None
    """
    if exists_nsir (nsId):
        nsir_coll.update_one({"nsId": nsId}, {"$set": {"network_mapping": mapping}})
    else: 
        nsir_record = {"nsId": nsId,
                       "network_mapping": mapping
                      }
        nsir_coll.insert_one(nsir_record)    

def set_network_renaming_mapping(renaming_mapping,nsId):
    """
    Function save information of renaming network mapping for a composite Network Service Instance.
    Useful when the composition is done from a reference.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    renaming_mapping: dict
        dictionary with information extracted from CROOE module related to internested connections when 
        the instantiation is done from a reference 
    Returns
    -------
    None
    """
    #no need to check if exists, because if not it is created by the set_network_mapping op
    nsir_coll.update_one({"nsId": nsId}, {"$set": {"renaming_mapping": renaming_mapping}})

def get_network_mapping(nsId):
    """
    Function to get the information of network mapping between composite network service and its nested
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    network_mapping: dict
        dictionary with information extracted from CROOE module related to internested connections 
    """
    nsir = nsir_coll.find_one({"nsId": nsId})
    if "network_mapping" in nsir:
        return nsir["network_mapping"]
    else:
        return {}

def get_renaming_network_mapping(nsId):
    """
    Function to get the information of renaming network mapping between composite network service and its nested
    when there is a reference
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
    renaming_mapping: dict
        dictionary with information extracted from CROOE module related to internested connections when the
        the instantiation is done from a reference  
    """
    nsir = nsir_coll.find_one({"nsId": nsId})
    if "renaming_mapping" in nsir:
        return nsir["renaming_mapping"]
    else:
        return {}

def get_vls(nsId):
    """
    Function to retrieve information of the virtual links deployed for a Network Service Instance.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
     vl_list: list
        list of deployed virtual links
    """
    nsir = nsir_coll.find_one({"nsId": nsId})
    if "vl_list" in nsir:
        return nsir["vl_list"]
    else:
        return []

def delete_vls (nsId,id_list):
    """
    Function to retrieve information of the virtual links deployed for a Network Service Instance.
    Parameters
    ----------
    nsId: string
        Identifier of the Network Service Instance.
    Returns
    -------
     vl_list: list
        list of deployed virtual links
    """
    # vl_list is a list of dictionaries
    vl_list = get_vls(nsId)
    for vl in vl_list:
        for ids in id_list:
            if ids in vl:
                vl_list.remove(vl)
    save_vls(vl_list, nsId)

def delete_nsir_record(nsId):
    """
    deletes one element of the nsd_coll
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    nsir_coll.delete_one({"nsId":nsId}) 


def empty_nsir_collection():
    """
    deletes all documents in the nsd_coll
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    nsir_coll.delete_many({})


####### GUI methods
def get_all_nsir():
    """
    Returns all the nsir in che collection
    Parameters
    ----------
    Returns
    -------
    list of dict
    """
    return list(nsir_coll.find())


def remove_nsir_by_id(id):
    """
    Remove a NSIR from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of NSIR
    Returns
    -------
    dict
    """
    output = nsir_coll.remove({"_id": ObjectId(id)})


def update_nsir(id, body):
    """
    Update a NSIR from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of NSIR
    body: body to update
    Returns
    -------
    ???
    """
    output = nsir_coll.update({"_id": ObjectId(id)}, {"$set": body})
    return output
