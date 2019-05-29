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
    nsdId: string
    version: string
    nsdCloudifyId: string
    nsdName: string
    nsdDescrition: string
    nsdJson: IFA014 json descriptor
"""

# mongodb imports
from bson import ObjectId
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
nsd_client = MongoClient(db_ip, db_port)
fgtso_db = nsd_client.fgtso

# create nsd catalogue
nsd_coll = fgtso_db.nsd

# format:
#     nsdId: string
#     nsdCloudifyId: string
#     version: string
#     nsdName: string
#     nsdJson: dict (IFA014 json descriptor)
#     domain: local / providerX  #for federation purposes


####### SO methods
def exists_nsd(nsdId, version=None):
    """
    Function to check if an NSD with identifier "nsdId" exists.
    Parameters
    ----------
    nsdId: string
        Identifier of the Network Service Descriptor
    Returns
    -------
    boolean
        returns True if a NSD with Id "nsdId" exists in "nsd_coll". Returns False otherwise.
    """
    nsd_json = None
    if version is None:
        nsd_json = nsd_coll.find_one({"nsdId": nsdId})
    else:
        nsd_json = nsd_coll.find_one({"nsdId": nsdId, "version": version})
    if nsd_json is None:
        return False
    return True


def get_nsd_cloudify_id(nsdId, version=None):
    """
    Returns the json descriptor of the NSD referenced by nsdId and version.
    Parameters
    ----------
    nsdId: string
        Identifier of the Network Service Descriptor
    version: string
        Version of the NSD
    Returns
    -------
    The cloudify internal id for this nsd
    """
    if version is None:
        nsd_info = nsd_coll.find_one({"nsdId": nsdId})
    else:
        nsd_info = nsd_coll.find_one({"nsdId": nsdId, "version": version})
    if nsd_info is None:
        return None
    return nsd_info["nsdCloudifyId"]


def get_nsd_json(nsdId, version=None):
    """
    Returns the json descriptor of the NSD referenced by nsdId and version.
    Parameters
    ----------
    nsdId: string
        Identifier of the Network Service Descriptor
    version: string
        Version of the NSD
    Returns
    -------
    dictionary with the NSD jsons saved in the catalogue that correspond to the nsdId
    """
    if version is None:
        nsd_json = nsd_coll.find_one({"nsdId": nsdId})
    else:
        nsd_json = nsd_coll.find_one({"nsdId": nsdId, "version": version})
    if nsd_json is None:
        return None
    return nsd_json["nsdJson"]

def delete_nsd_json(nsdId, version=None):
    """
    Returns True if the referenced descriptor has been deleted from the catalog.
    Parameters
    ----------
    nsdId: string
        Identifier of the Network Service Descriptor
    version: string
        Version of the NSD
    Returns
    -------
    boolean
    """
    nsd_query = None
    if (version is not None and version != "NONE"):
        nsd_query = {"nsdId": nsdId, "version": version}
    else:
        nsd_query= {"nsdId": nsdId}
    if nsd_query is None:
        return False
    else:
        nsd_coll.delete_one(nsd_query)
        return True


def get_nsd_domain(nsdId, version = None):
    """
    Returns the domain, where this NSD can be instantiated, referenced by nsdId and version.
    Parameters
    ----------
    nsdId: string
        Identifier of the Network Service Descriptor
    version: string
        Version of the NSD
    Returns
    -------
    string
        the domain where this service can be instantiated
    """
    if version is None:
        nsd_json = nsd_coll.find_one({"nsdId": nsdId})
    else:
        nsd_json = nsd_coll.find_one({"nsdId": nsdId, "version": version})
    if nsd_json is None:
        return None
    return nsd_json["domain"]

def get_nsd_shareability(nsdId, version = None):
    """
    Returns the shareable flag, whether this NSD can be shared with other instantances, referenced by nsdId and version.
    Parameters
    ----------
    nsdId: string
        Identifier of the Network Service Descriptor
    version: string
        Version of the NSD
    Returns
    -------
    string
        the domain where this service can be instantiated
    """
    if version is None:
        nsd_json = nsd_coll.find_one({"nsdId": nsdId})
    else:
        nsd_json = nsd_coll.find_one({"nsdId": nsdId, "version": version})
    if nsd_json is None:
        return None
    return nsd_json["shareable"]


def insert_nsd(nsd_record):
    """
    Inserts a nsd record in the DB
    Parameters
    ----------
    nsd_record: json
        json containing the nsd information, format:
            nsdId: string
            nsdCloudifyId
            version: string
            nsdName: string
            nsdJson: dict (IFA014 json descriptor)
            domain: string #for federation purposes
    Returns
    -------
    None
    """

    nsd_coll.insert_one(nsd_record)


def delete_nsd_json(nsdId, version=None):
    """
    Returns True if the referenced descriptor has been deleted from the catalog.
    Parameters
    ----------
    nsdId: string
        Identifier of the Network Service Descriptor
    version: string
        Version of the NSD
    Returns
    -------
    boolean
    """
    nsd_query = None
    if (version is not None and version != "NONE"):
        nsd_query = {"nsdId": nsdId, "version": version}
    else:
        nsd_query= {"nsdId": nsdId}
    if nsd_query is None:
        return False
    else:
        nsd_coll.delete_one(nsd_query)
        return True

def empty_nsd_collection():
    """
    deletes all documents in the nsd_coll
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    nsd_coll.delete_many({})


####### GUI methods
def get_all_nsd():
    """
    Returns all the nsd in che collection
    Parameters
    ----------
    Returns
    -------
    list of dict
    """
    return list(nsd_coll.find())


def update_nsd(id, body):
    """
    Update a Nsd from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of nsd
    body: body to update
    Returns
    -------
    ???
    """
    output = nsd_coll.update({"_id": ObjectId(id)}, {"$set": body})
    return output


def remove_nsd_by_id(id):
    """
    Remove a nsd from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of nsd
    Returns
    -------
    dict
    """
    output = nsd_coll.remove({"_id": ObjectId(id)})
    # print(output)

