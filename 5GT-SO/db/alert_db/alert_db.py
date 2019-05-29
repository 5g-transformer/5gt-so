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
alerts_coll = fgtso_db.alerts


# alerts collection functions
def create_alert_record(alert_record):
    """
    Inserts a nsd record in the DB
    Parameters
    ----------
    alert_record: json
        json containing the alert information, format:
            alert_id: string
            status: string
            nsd_id: string
            rule_id: string
            timestamp: string
    Returns
    -------
    None
    """
    alerts_coll.insert_one(alert_record)

def get_alert(alert_id):
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
    alert = alerts_coll.find_one({"alert_id": alert_id})
    return alert

def set_timestamp(alert_id, timestamp):
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
    alerts_coll.update_one({"alert_id": alert_id}, {"$set": {"timestamp": timestamp}})

def get_timestamp(alert_id):
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
    alert = alerts_coll.find_one({"alert_id": alert_id})
    return alert["timestamp"]

def exists_alert_id(alert_id):
    """
    Function to check if an alert with identifier "alert_id" exists.
    Parameters
    ----------
    alert_id: string
        Identifier of the Alert ID.
    Returns
    -------
    boolean
        returns True if a Alert with Id "nsId" exists in "alerts_coll". Returns False otherwise.
    """
    ns = alerts_coll.find_one({"alert_id": alert_id})
    if ns is None:
        return False
    return True

