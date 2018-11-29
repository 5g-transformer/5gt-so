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
Small script to load descriptors into the SO NSD/VNFD catalogues.
"""

# python imports
from json import load

# project imports
import sys
sys.path.append("../../../5GT-SO")
from nbi import log_process
from db.nsd_db.nsd_db import insert_nsd, empty_nsd_collection
from db.vnfd_db.vnfd_db import insert_vnfd, empty_vnfd_collection
from db.ns_db.ns_db import empty_ns_collection
from db.operation_db.operation_db import empty_operation_collection
from db.resources_db.resources_db import empty_resources_collection
from db.nsir_db.nsir_db import empty_nsir_collection


def main():

    # empty databases
    empty_nsd_collection()
    empty_vnfd_collection()
    empty_ns_collection()
    empty_operation_collection()
    empty_resources_collection()
    empty_nsir_collection()

    # path to descriptors folders
    path = "../../descriptors/"

    # list of file names that contain ns and vnf descriptors
    ns_descriptors = ["CDN_all_NSD_0_2.json"]
    vnf_descriptors = ["CDN_SPR1_VNFD_0_2.json", "CDN_SPR21_VNFD_0_2.json", "CDN_SPR22_VNFD_0_2.json",
                       "CDN_WEBSERVER_VNFD_0_2.json"]

    # NSD SECTION

    # correspondance of nsdId and nsdCloudifyId
    nsdCloudifyId = {"vCDN_v02": "unknown"}

    # for each nsd create record to be inserted
    nsd_json = {}  # load json file here
    for nsd_file in ns_descriptors:
        with open(path + nsd_file) as nsd_json:
            nsd_json = load(nsd_json)
        nsd_record = {"nsdId": nsd_json["nsd"]["nsdIdentifier"],
                      "nsdCloudifyId": nsdCloudifyId[nsd_json["nsd"]["nsdIdentifier"]],
                      "version": nsd_json["nsd"]["version"],
                      "nsdName": nsd_json["nsd"]["nsdName"],
                      "nsdJson": nsd_json}
        insert_nsd(nsd_record)

    # VNFD SECTION

    # for each nsd create record to be inserted
    vnfd_json = {}  # load json file here
    for vnfd_file in vnf_descriptors:
        with open(path + vnfd_file) as vnfd_json:
            vnfd_json = load(vnfd_json)
        vnfd_record = {"vnfdId": vnfd_json["vnfdId"],
                       "vnfdVersion": vnfd_json["vnfdVersion"],
                       "vnfdName": vnfd_json["vnfProductName"],
                       "vnfdJson": vnfd_json}
        insert_vnfd(vnfd_record)

    log_process.terminate()


if __name__ == "__main__":
    main()
