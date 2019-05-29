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
Network Service Catalogue.
DB structure:
Object(_id) = string # automically created by mongo
username = string
password = string
role = string
"""

# mongodb imports
from bson import ObjectId
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
user_client = MongoClient(db_ip, db_port)
fgtso_db = user_client.fgtso

# use user collection
user_coll = fgtso_db.user


####### GUI methods
def insert_user(user_record):
    """
    Inserts a nsd record in the DB
    Parameters
    ----------
    user_record: json
        json containing the user information, format:
            username: string
            password: string
            role: string (Admin or Member)
    Returns
    -------
    None
    """

    output = user_coll.insert(user_record)
    # print("output_insert: " + output)


def get_all_user():
    """
    Returns all the users in che collection
    Parameters
    ----------
    Returns
    -------
    list of dict
    """
    return list(user_coll.find())


def remove_user_by_id(id):
    """
    Remove a User from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of user
    Returns
    -------
    dict
    """
    output = user_coll.remove({"_id": ObjectId(id)})


def update_user(id, body):
    """
    Update a User from the collection filtered by the id parameter
    Parameters
    ----------
    id: _id of user
    Returns
    -------
    ???
    """
    output = user_coll.update({"_id": ObjectId(id)}, {"$set": body})
    return output


def get_specific_user(user_record):
    """
    Remove a User from the collection filtered by the username parameter
    Parameters
    ----------
    username: username of user
    Returns
    -------
    ???
    """
    output = user_coll.find_one(user_record)
    return output


# def get_vnfd_json(vnfdId, version=None):
#     """
#     Returns the json descriptor of the VNFD referenced by vnfdId.
#     Parameters
#     ----------
#     vnfdId: string
#         Identifier of the VNFD
#     version: string
#         Version of the VNFD
#     Returns
#     -------
#     dictionary with the VNFD json saved in the catalogue that correspond to the vnfdId/version
#     """
#     if (version is not None and version !="NONE"):
#     #if version != "NONE":
#         vnfd_json = vnfd_coll.find_one({"vnfdId": vnfdId, "vnfdVersion": version})
#         if vnfd_json is None:
#             return None
#         return vnfd_json["vnfdJson"]
#     else:
#         vnfd_json = vnfd_coll.find_one({"vnfdId": vnfdId})
#         if vnfd_json is None:
#             return None
#         return vnfd_json["vnfdJson"]

def empty_user_collection():
    """
    deletes all documents in the vnfd_coll
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    user_coll.delete_many({})
