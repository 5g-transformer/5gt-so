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
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
nsir_client = MongoClient(db_ip, db_port)
fgtso_db = nsir_client.fgtso

# create nsir collection
nsir_coll = fgtso_db.nsir


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
    # TODO: stub
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


def get_placement_info(nsId):
    """
    Function to save the resources assigned to a Network Service Instance by the Placement Algorithm.
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

    return nsir["placement_info"]


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
    nsir_coll.update_one({"nsId": nsId}, {"$set": {"vl_list": vl_list}})


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

    return nsir["vl_list"]


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
