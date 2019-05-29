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
Network Service Catalogue.
DB structure:
vnfdId: string
vnfdName: string
vnfdDescrition: string
vnfdJson: IFA014 json descriptor
"""


# mongodb imports
from bson import ObjectId
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
vnfd_client = MongoClient(db_ip, db_port)
fgtso_db = vnfd_client.fgtso

# create vnfd catalogue
vnfd_coll = fgtso_db.vnfd


####### SO methods
def exists_vnfd(vnfdId, version=None):
    """
    Function to check if an VNFD with identifier "vnfdId" exists.
    Parameters
    ----------
    vnfdId: string
        Identifier of the Virtual Network Function Descriptor
    Returns
    -------
    boolean
        returns True if a VNFD with Id "vnfdId" exists in "vnfd_coll". Returns False otherwise.
    """
    vnfd_json = None
    if version is None:
        vnfd_json = vnfd_coll.find_one({"vnfdId": vnfdId})
    else:
        vnfd_json = vnfd_coll.find_one({"vnfdId": vnfdId, "vnfdVersion": version})
    if vnfd_json is None:
        return False
    return True


def insert_vnfd(vnfd_record):
    """
    Inserts a nsd record in the DB
    Parameters
    ----------
    vnfd_record: json
        json containing the vnfd information, format:
            vnfdId: string
            vnfdVersion: string
            vnfdName: string
            vnfdJson: dict (IFA014 json descriptor)
    Returns
    -------
    None
    """

    vnfd_coll.insert_one(vnfd_record)


def get_vnfd_json(vnfdId, version=None):
    """
    Returns the json descriptor of the VNFD referenced by vnfdId.
    Parameters
    ----------
    vnfdId: string
        Identifier of the VNFD
    version: string
        Version of the VNFD
    Returns
    -------
    dictionary with the VNFD json saved in the catalogue that correspond to the vnfdId/version
    """
    if (version is not None and version !="NONE"):
        vnfd_json = vnfd_coll.find_one({"vnfdId": vnfdId, "vnfdVersion": version})
        if vnfd_json is None:
            return None
        return vnfd_json["vnfdJson"]
    else:
        vnfd_json = vnfd_coll.find_one({"vnfdId": vnfdId})
        if vnfd_json is None:
            return None
        return vnfd_json["vnfdJson"]

def delete_vnfd_json(vnfdId, version=None):
    """
    Returns True if the referenced descriptor has been deleted from the catalog.
    Parameters
    ----------
    vnfdId: string
        Identifier of the Network Service Descriptor
    version: string
        Version of the NSD
    Returns
    -------
    boolean
    """
    vnfd_query = None
    if (version is not None and version != "NONE"):
        vnfd_query = {"vnfdId": vnfdId, "version": version}
    else:
        vnfd_query= {"vnfdId": vnfdId}        
    if vnfd_query is None:
        return False
    else:
        vnfd_coll.delete_one(vnfd_query)
        return True


def empty_vnfd_collection():
    """
    deletes all documents in the vnfd_coll
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    vnfd_coll.delete_many({})


####### GUI methods
def get_all_vnfd():
    """
    Returns all the vnfds in che collection
    Parameters
    ----------
    Returns
    -------
    list of dict
    """
    return list(vnfd_coll.find())


def update_vnfd(id, body):
    """
    Update a vnfd from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of vnfd
    body: body to update
    Returns
    -------
    ???
    """
    output = vnfd_coll.update({"_id": ObjectId(id)}, {"$set": body})
    # print(output)
    return output


def remove_vnfd_by_id(id):
    """
    Remove a Vnfd from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of vnfd
    Returns
    -------
    dict
    """
    output = vnfd_coll.remove({"_id": ObjectId(id)})
    # print(output)
