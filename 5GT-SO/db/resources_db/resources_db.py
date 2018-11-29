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
DB with the information of virtual resources available at the MTP.
"""

# mongodb imports
from pymongo import MongoClient

# project imports
from db import db_ip, db_port
from nbi import log_queue

# create the 5gtso db
resources_client = MongoClient(db_ip, db_port)
fgtso_db = resources_client.fgtso

# create resources collection
resources_coll = fgtso_db.resources


def lock_resources_db():
    """
    Get read/write lock on the DB.
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    pass


def unlock_resources_db():
    """
    Release read/write lock on the DB.
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    pass


def get_mtp_resources():
    """
    Function to get the available virtual resources of the MTP.
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    return {}


def update_resources_information(placement_info):
    """
    Substract from mtp resources the resources used by the placement algorithm.
    Parameters
    ----------
    placement_info: dict
        Resources booked by the Placement Algorithm.
    Returns
    -------
    None
    """
    pass


def add_resources_information(placement_info):
    """
    Add to mtp resources the resources used by the placement algorithm.
    Parameters
    ----------
    placement_info: dict
        Resources booked by the Placement Algorithm.
    Returns
    -------
    None    """
    pass


def empty_resources_collection():
    """
    deletes all documents in the resources_coll
    Parameters
    ----------
    None
    Returns
    -------
    None
    """
    resources_coll.delete_many({})
