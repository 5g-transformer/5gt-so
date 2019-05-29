# Copyright 2019 CTTC www.cttc.es
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
MEC application Catalogue.
DB structure:
appdId: string
appdName: string
appdDescrition: string
appdJson: IFA014 json descriptor
"""


# mongodb imports
from bson import ObjectId
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
appd_client = MongoClient(db_ip, db_port)
fgtso_db = appd_client.fgtso

# create appd catalogue
appd_coll = fgtso_db.appd


####### SO methods
def exists_appd(appdId, version=None):
    """
    Function to check if an appd with identifier "appdId" exists.
    Parameters
    ----------
    appdId: string
        Identifier of the Virtual Network Function Descriptor
    Returns
    -------
    boolean
        returns True if a appd with Id "appdId" exists in "appd_coll". Returns False otherwise.
    """
    appd_json = None
    if version is None:
        appd_json = appd_coll.find_one({"appdId": appdId})
    else:
        appd_json = appd_coll.find_one({"appdId": appdId, "appdVersion": version})
    if appd_json is None:
        return False
    return True


def insert_appd(appd_record):
    """
    Inserts a nsd record in the DB
    Parameters
    ----------
    appd_record: json
        json containing the appd information, format:
            appdId: string
            appdVersion: string
            appdName: string
            appdJson: dict (IFA014 json descriptor)
    Returns
    -------
    None
    """

    appd_coll.insert_one(appd_record)


def get_appd_json(appdId, version=None):
    """
    Returns the json descriptor of the appd referenced by appdId.
    Parameters
    ----------
    appdId: string
        Identifier of the appd
    version: string
        Version of the appd
    Returns
    -------
    dictionary with the appd json saved in the catalogue that correspond to the appdId/version
    """
    if (version is not None and version !="NONE"):
        appd_json = appd_coll.find_one({"appdId": appdId, "appdVersion": version})
        if appd_json is None:
            return None
        return appd_json["appdJson"]
    else:
        appd_json = appd_coll.find_one({"appdId": appdId})
        if appd_json is None:
            return None
        return appd_json["appdJson"]

def delete_appd_json(appdId, version=None):
    """
    Returns True if the referenced descriptor has been deleted from the catalog.
    Parameters
    ----------
    appdId: string
        Identifier of the Network Service Descriptor
    version: string
        Version of the NSD
    Returns
    -------
    boolean
    """
    appd_query = None
    if (version is not None and version != "NONE"):
        appd_query = {"appdId": appdId, "version": version}
    else:
        appd_query= {"appdId": appdId}        
    if appd_query is None:
        return False
    else:
        appd_coll.delete_one(appd_query)
        return True


def empty_appd_collection():
    """
    deletes all documents in the appd_coll
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    appd_coll.delete_many({})


####### GUI methods
def get_all_appd():
    """
    Returns all the appds in che collection
    Parameters
    ----------
    Returns
    -------
    list of dict
    """
    return list(appd_coll.find())


def update_appd(id, body):
    """
    Update a appd from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of appd
    body: body to update
    Returns
    -------
    ???
    """
    output = appd_coll.update({"_id": ObjectId(id)}, {"$set": body})
    # print(output)
    return output


def remove_appd_by_id(id):
    """
    Remove a appd from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of appd
    Returns
    -------
    dict
    """
    output = appd_coll.remove({"_id": ObjectId(id)})
    # print(output)
