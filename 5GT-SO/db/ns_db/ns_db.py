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

# mongodb imports
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
ns_client = MongoClient(db_ip, db_port)
fgtso_db = ns_client.fgtso

# create network service instances collection
ns_coll = fgtso_db.ns


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
                 "sapInfo": None
                 }

    ns_coll.insert_one(ns_record)


def save_instantiation_info(nsId, body):
    """
    Save in ns_coll the information received in the body of the ns instantiation request.
    Also sets the status to "INSTANTIATING"
    ----------
    nsId: string
        Id of the Network Service Instance
    body: Request Body
        body received by the
    Returns
    -------
    None
    """
    ns_coll.update_one({"nsId": nsId}, {"$set": {"status": "INSTANTIATING",
                                                 "flavourId": body.flavour_id,
                                                 "nsInstantiationLevelId": body.ns_instantiation_level_id}})


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
    ns_coll.update_one({"nsId": nsId}, {"$set": {"sapInfo": sapInfo}})


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
    if ns is None:
        return None
    return ns["sapInfo"]


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
