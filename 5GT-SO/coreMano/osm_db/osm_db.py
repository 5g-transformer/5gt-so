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
Database for OSM
DB structure:
cidrs: list of int
vlans: list of int
"""

# mongodb imports
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
ns_client = MongoClient(db_ip, db_port)
fgtso_db = ns_client.fgtso

# create osm collection
osm_coll = fgtso_db.osm

osm_coll.insert_one({"cidrs": [], "vlans": []})


def add_used_cidr(cidr):
    """
    Function description
    Parameters
    ----------
    param1: type
        param1 description
    Returns
    -------
    name: type
        return description
    """
    osm_coll.update({}, {'$push': {'cidrs': cidr}})


def remove_used_cidr(cidr):
    """
    Function description
    Parameters
    ----------
    param1: type
        param1 description
    Returns
    -------
    name: type
        return description
    """
    osm_coll.update({}, {'$pull': {'cidrs': cidr}})


def get_used_cidrs():
    """
    Function description
    Parameters
    ----------
    param1: type
        param1 description
    Returns
    -------
    name: type
        return description
    """
    all = osm_coll.find_one()
    if all is None:
        return None
    return all["cidrs"]


def add_used_vlan(vlan):
    """
    Function description
    Parameters
    ----------
    param1: type
        param1 description
    Returns
    -------
    name: type
        return description
    """
    osm_coll.update({}, {'$push': {'vlans': vlan}})


def remove_used_vlan(vlan):
    """
    Function description
    Parameters
    ----------
    param1: type
        param1 description
    Returns
    -------
    name: type
        return description
    """
    osm_coll.update({}, {'$pull': {'vlans': vlan}})


def get_used_vlans():
    """
    Function description
    Parameters
    ----------
    param1: type
        param1 description
    Returns
    -------
    name: type
        return description
    """
    all = osm_coll.find_one()
    if all is None:
        return None
    return all["vlans"]


def empty_osm_collection():
    """
    deletes all documents in the osm_coll
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    osm_coll.delete_many({})
