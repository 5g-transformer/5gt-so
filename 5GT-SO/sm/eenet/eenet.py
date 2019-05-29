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
from json import dumps, loads

# project imports
from db.nsir_db import nsir_db
from nbi import log_queue
from sbi import sbi


########################################################################################################################
# PUBLIC METHODS                                                                                                       #
########################################################################################################################


def deploy_vls(vl_list, nsId):
    """
    Function description
    Parameters
    ----------
    vl_list: list of dicts
        list of vls to deploy where each element of the list is a dict with the following format:
    nsId: string
        Identifier of the logical link to perform the update operation
    Returns
    -------
    None
    """
    # deploy: you make only a single call with all the logical links for the network service
    mtp_vl_ids = []
    if (len (vl_list["logicalLinkPathList"]) > 0):
        mtp_vl_ids = sbi.deploy_vl(vl_list, nsId)
    vl_info = []
    for i in range(0, len(mtp_vl_ids)):
        vl_info.append({mtp_vl_ids[i]: vl_list["logicalLinkPathList"][i]})
    nsir_db.save_vls(vl_info, nsId)

def update_vls(nsId, vl_list, vls_ids_to_remove):
    """
    Method to update logical links on a network service when required, such as a scaling procedure
    Parameters
    ----------
    nsId: string
        Identifier of the logical link to perform the update operation
    vl_list: list of dicts
        list of vls to deploy by the mtp
    vl_ids_to_remove:
        list of vls_ids to remove
    Returns
    -------
    None
    """
    #links to add
    mtp_vl_ids = []
    vl_info = []
    mtp_vl_ids = sbi.deploy_vl(vl_list, nsId)
    for i in range(0, len(mtp_vl_ids)):
        vl_info.append({mtp_vl_ids[i]: vl_list["logicalLinkAttributes"][i]})
    vl_list_prev = nsir_db.get_vls(nsId)
    vl_total = vl_list_prev + vl_info
    nsir_db.save_vls(vl_total, nsId)
    #ids to remove
    for ids in vls_ids_to_remove:
        vl_info.append({"interNfviPopConnnectivityId":ids})
    sbi.uninstall_vl(vl_info, nsId)
    nsir_db.delete_vls(nsId,vls_ids_to_remove)

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
    vl = nsir_db.get_vls(nsId)
    # with one request we remove all the established logical links
    vl_list = []
    for index in range(0,len(vl)):
        key = next(iter(vl[index]))
        log_queue.put(["DEBUG", "remove ll: %s"%key])
        vl_list.append({"interNfviPopConnnectivityId":key})
    if (len(vl_list) > 0):
        sbi.uninstall_vl(vl_list, nsId)

