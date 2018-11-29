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
from unittest import TestCase, main
from http.client import HTTPConnection
from json import dumps, loads, load
from six.moves.configparser import RawConfigParser

# mongodb imports
from pymongo import MongoClient

# project imports


class TestRegression(TestCase):

    def setUp(self):
        self.ip = "localhost"
        self.port = "8080"
        self.headers = {'Content-Type': 'application/json',
                        'Accept': 'application/json'}
        self.timeout = 10
        # connect
        self.conn = HTTPConnection(self.ip, self.port, timeout=self.timeout)
        # on board necessary descriptors
        # drop all databases
        # create the 5gtso db
        # python imports

        # load db IP port
        config = RawConfigParser()
        config.read("../db/db.properties")
        db_ip = config.get("MongoDB", "db.ip")
        db_port = int(config.get("MongoDB", "db.port"))
        operation_client = MongoClient(db_ip, db_port)
        fgtso_db = operation_client.fgtso
        fgtso_db.nsd.delete_many({})
        fgtso_db.vnfd.delete_many({})
        fgtso_db.ns.delete_many({})
        fgtso_db.nsir.delete_many({})
        fgtso_db.operation.delete_many({})
        fgtso_db.resources.delete_many({})
        # load desccriptors
        # path to descriptors folders

        path = "../descriptors/"
        # list of file names that contain ns and vnf descriptors
        ns_descriptors = ["CDN_all_NSD_0_2.json"]
        vnf_descriptors = ["CDN_SPR1_VNFD_0_2.json", "CDN_SPR21_VNFD_0_2.json", "CDN_SPR22_VNFD_0_2.json",
                           "CDN_WEBSERVER_VNFD_0_2.json"]
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
            fgtso_db.nsd.insert_one(nsd_record)
        # for each nsd create record to be inserted
        vnfd_json = {}  # load json file here
        for vnfd_file in vnf_descriptors:
            with open(path + vnfd_file) as vnfd_json:
                vnfd_json = load(vnfd_json)
            vnfd_record = {"vnfdId": vnfd_json["vnfdId"],
                           "vnfdVersion": vnfd_json["vnfdVersion"],
                           "vnfdName": vnfd_json["vnfProductName"],
                           "vnfdJson": vnfd_json}
            fgtso_db.vnfd.insert_one(vnfd_record)

    def tearDown(self):
        self.conn.close()

    def test_1_basic_instantiation_and_termination(self):
        """
        Check basic operations tests expecting a 200/201 result.
        """

        # request an nsId
        path = "/5gt/so/v1/ns"
        data = {"nsDescription": "nsDescription",
                "nsName": "nsName",
                "nsdId": "vCDN_v02"
                }
        self.conn.request("POST", path, dumps(data), self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        data = rsp.read().decode()
        self.assertEqual(rsp.status, 201)
        data = loads(data)
        nsId = data["nsId"]

        # instantiate the service
        path = "/5gt/so/v1/ns/" + nsId + "/instantiate"
        data = {"flavourId": "df_vCDN",
                "nsInstantiationLevelId": "il_vCDN_small"
                }
        self.conn.request("PUT", path, dumps(data), self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        data = rsp.read().decode()
        self.assertEqual(rsp.status, 200)
        data = loads(data)
        operationId = data["operationId"]

        # get operation status
        path = "/5gt/so/v1/operation/" + operationId
        self.conn.request("GET", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 200)

        # get ns information
        path = "/5gt/so/v1/ns/" + nsId
        self.conn.request("GET", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 200)

        # terminate the service
        path = "/5gt/so/v1/ns/" + nsId + "/terminate"
        self.conn.request("PUT", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 200)

        # the following tests expect the NSD vCDN 0.2 and its VNFs to be loaded in the NSD/VNFD catalogues
        # get a NSD
        path = "/5gt/so/v1/ns/nsd/vCDN_v02/0.2"
        self.conn.request("GET", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 200)

        # get a VNFD
        path = "/5gt/so/v1/ns/vnfd/spr22/0.2"
        self.conn.request("GET", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 200)

    def test_2_nbi_400_404_errors(self):
        """
        Check that NBI returns error 400/404.
        """

        # request an nsId
        path = "/5gt/so/v1/ns"
        data = {"nsDescription": "nsDescription",
                "nsName": "nsName"
                }
        self.conn.request("POST", path, dumps(data), self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 400)

        # request an nsId
        path = "/5gt/so/v1/ns"
        data = {"nsDescription": "nsDescription",
                "nsName": "nsName",
                "nsdId": "vCDN_v02"
                }
        self.conn.request("POST", path, dumps(data), self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        data = rsp.read().decode()
        self.assertEqual(rsp.status, 201)
        data = loads(data)
        nsId = data["nsId"]

        # instantiate the service
        path = "/5gt/so/v1/ns/" + nsId + "/instantiate"
        data = {"flavourId": 1}
        self.conn.request("PUT", path, dumps(data), self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 400)

        # instantiate the service
        path = "/5gt/so/v1/ns/unknowonId/instantiate"
        data = {"flavourId": "flavourId",
                "nsInstantiationLevelId": "nsInstantiationLevelId"
                }
        self.conn.request("PUT", path, dumps(data), self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 404)

        # get operation status
        path = "/5gt/so/v1/operation/unknownId"
        self.conn.request("GET", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 404)

        # get ns information
        path = "/5gt/so/v1/ns/unkownId"
        self.conn.request("GET", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 404)

        # terminate the service
        path = "/5gt/so/v1/ns/unknownId/terminate"
        self.conn.request("PUT", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 404)

        # get a NSD
        path = "/5gt/so/v1/ns/nsd/CDN_v02/0.2"
        self.conn.request("GET", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 404)

        # get a NSD
        path = "/5gt/so/v1/ns/nsd/vCDN_v02/0.3"
        self.conn.request("GET", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 404)

        # get a VNFD
        path = "/5gt/so/v1/ns/vnfd/tpr22/0.2"
        self.conn.request("GET", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 404)

        # get a VNFD
        path = "/5gt/so/v1/ns/vnfd/spr22/0.3"
        self.conn.request("GET", path, None, self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        self.assertEqual(rsp.status, 404)


if __name__ == '__main__':
    main()
