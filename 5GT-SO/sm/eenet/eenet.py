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
File description
"""

# python imports
from http.client import HTTPConnection
from six.moves.configparser import RawConfigParser
from json import dumps, loads
# project imports
from db.nsir_db import nsir_db
from nbi import log_queue


########################################################################################################################
# PRIVATE METHODS                                                                                                      #
########################################################################################################################


def deploy_vl(vl):
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
    mtp_path = config.get("MTP", "mtp.path")
    mtp_uri = "http://" + mtp_ip + ":" + mtp_port + mtp_path + "/resources"
    # connect to MTP aznd make the request
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    deployed_vl_info = {}
    try:
        conn = HTTPConnection(mtp_ip, mtp_port)
        conn.request("POST", mtp_uri, dumps(vl), header)
        rsp = conn.getresponse()
        deployed_vl_info = rsp.read()
        deployed_vl_info = deployed_vl_info.decode("utf-8")
        deployed_vl_info = loads(deployed_vl_info)
        log_queue.put(["DEBUG", "deployed vls info from MTP are:"])
        log_queue.put(["DEBUG", dumps(deployed_vl_info, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the MTP server is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the MTP server is not running or the connection configuration is wrong"])
    return deployed_vl_info["interNfviPopConnnectivityId"]


def uninstall_vl(vl):
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
    # read mtp properties
    config = RawConfigParser()
    config.read("../../mtp.properties")
    mtp_ip = config.get("MTP", "mtp.ip")
    mtp_port = config.get("MTP", "mtp.port")
    mtp_path = config.get("MTP", "mtp.path")
    mtp_uri = "http://" + mtp_ip + ":" + mtp_port + mtp_path + "/resources"
    # connect to MTP aznd make the request
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    body = {"interNfviPopConnnectivityId": vl,
            "metaData": []}
    try:
        conn = HTTPConnection(mtp_ip, mtp_port)
        conn.request("DELETE", mtp_uri, dumps(body), header)
        rsp = conn.getresponse()
        deployed_vl_info = rsp.read()
        conn.close()
    except ConnectionRefusedError:
        # the MTP server is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the MTP server is not running or the connection configuration is wrong"])


########################################################################################################################
# PUBLIC METHODS                                                                                                       #
########################################################################################################################


def deploy_vls(vl_list, nsId):
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
    # save virtual links info related to nsId so it can be freed at terminate
    nsir_db.save_vls(vl_list, nsId)
    # deploy
    mtp_vl_ids = []
    for vl in vl_list:
        vlid = deploy_vl(vl)
        mtp_vl_ids.append(vlid)
    nsir_db.save_vls(mtp_vl_ids, nsId)


def uninstall_vls(nsId):
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
    # get virtual links of the nsID
    vl_list = nsir_db.get_vls(nsId)
    # uninstall
    for vl in vl_list:
        uninstall_vl(vl)
