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
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
vnfd_client = MongoClient(db_ip, db_port)
fgtso_db = vnfd_client.fgtso

# create vnfd catalogue
vnfd_coll = fgtso_db.vnfd


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


def get_vnfd_json(vnfdId, version):
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
    if version is not None:
        vnfd_json = vnfd_coll.find_one({"vnfdId": vnfdId, "vnfdVersion": version})
        if vnfd_json is None:
            return None
        return vnfd_json["vnfdJson"]
    else:
        vnfd_json = vnfd_coll.find_one({"vnfdId": vnfdId})
        if vnfd_json is None:
            return None
        return vnfd_json["vnfdJson"]


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
