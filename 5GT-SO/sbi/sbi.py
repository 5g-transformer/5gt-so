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

# python imports
from http.client import HTTPConnection
from six.moves.configparser import RawConfigParser
from json import loads, dumps
# project imports
from nbi import log_queue

# load mtp properties
config = RawConfigParser()
config.read("../../mtp.properties")
mtp_ip = config.get("MTP", "mtp.ip")
mtp_port = config.get("MTP", "mtp.port")
mtp_base_path = config.get("MTP", "mtp.base_path")


def get_mtp_resources():
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
    # read mtp properties
    config = RawConfigParser()
    config.read("../../mtp.properties")
    mtp_ip = config.get("MTP", "mtp.ip")
    mtp_port = config.get("MTP", "mtp.port")
    mtp_path = config.get("MTP", "mtp.base_path")
    mtp_uri = "http://" + mtp_ip + ":" + mtp_port + mtp_path + "/abstract-resources"
    # connect to MTP and make the request
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    resources = {}
    # code below commented until MTP is ready
    try:
        conn = HTTPConnection(mtp_ip, mtp_port)
        conn.request("GET", mtp_uri, None, header)
        rsp = conn.getresponse()
        resources = rsp.read()
        resources = resources.decode("utf-8")
        resources = loads(resources)
        log_queue.put(["INFO", "Resources from MTP are:"])
        log_queue.put(["INFO", dumps(resources, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the MTP server is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the MTP server is not running or the connection configuration is wrong"])

    return resources


def get_mtp_federated_resources():
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
    # read mtp properties
    config = RawConfigParser()
    config.read("../../mtp.properties")
    mtp_ip = config.get("MTP", "mtp.ip")
    mtp_port = config.get("MTP", "mtp.port")
    mtp_path = config.get("MTP", "mtp.base_path")
    mtp_uri = "http://" + mtp_ip + ":" + mtp_port + mtp_path + "/abstract-federated-resources"
    # connect to MTP and make the request
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    resources = {}
    try:
        conn = HTTPConnection(mtp_ip, mtp_port)
        conn.request("GET", mtp_uri, None, header)
        rsp = conn.getresponse()
        resources = rsp.read()
        resources = resources.decode("utf-8")
        resources = loads(resources)
        log_queue.put(["INFO", "Federated Resources from MTP are:"])
        log_queue.put(["INFO", dumps(resources, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the MTP server is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the MTP server is not running or the connection configuration is wrong"])

    return resources


def deploy_vl(vl, nsId):
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
    # read mtp properties
    mtp_uri = "http://" + mtp_ip + ":" + mtp_port + mtp_base_path + "/abstract-network-resources"
    # connect to MTP aznd make the request
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    deployed_vl_info = {}
    vl["metaData"].append({"key": "ServiceId", "value": nsId})
    try:
        log_queue.put(["INFO", "deploy vl: body is:"])
        log_queue.put(["INFO", dumps(vl, indent=4)])
        conn = HTTPConnection(mtp_ip, mtp_port)
        conn.request("POST", mtp_uri, dumps(vl), header)
        rsp = conn.getresponse()
        deployed_vl_info = rsp.read()
        deployed_vl_info = deployed_vl_info.decode("utf-8")
        deployed_vl_info = loads(deployed_vl_info)
        log_queue.put(["INFO", "deployed vls info from MTP are:"])
        log_queue.put(["INFO", dumps(deployed_vl_info, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the MTP server is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the MTP server is not running or the connection configuration is wrong"])
    vl_ids = []
    if (len(deployed_vl_info) > 0):
        for ids in range(0, len(deployed_vl_info)):
            vl_ids.append(deployed_vl_info[ids]["interNfviPopConnnectivityId"])
    return vl_ids


def uninstall_vl(vl_list, nsId):
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
    # ask mtp to deploy vl
    mtp_uri = "http://" + mtp_ip + ":" + mtp_port + mtp_base_path + "/abstract-network-resources"
    # connect to MTP and make the request
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    body = {"interNfviPopConnnectivityIdList": [],
            "metaData": []}
    body["interNfviPopConnnectivityIdList"] = vl_list
    body["metaData"].append({"key": "ServiceId", "value": nsId})
    try:
        conn = HTTPConnection(mtp_ip, mtp_port)
        conn.request("DELETE", mtp_uri, dumps(body), header)
        rsp = conn.getresponse()
        deployed_vl_info = rsp.read()
        conn.close()
    except ConnectionRefusedError:
        # the MTP server is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the MTP server is not running or the connection configuration is wrong"])
