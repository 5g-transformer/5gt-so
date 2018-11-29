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
    Returns
    -------
    None
    """

    nsd_coll.insert_one(nsd_record)


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
