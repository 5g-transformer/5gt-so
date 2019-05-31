# Copyright (C) 2018 CTTC/CERCA
# License: To be defined. Currently use is restricted to partners of the 5G-Transformer project,
#          http://5g-transformer.eu/, no use or redistribution of any kind outside the 5G-Transformer project is
#          allowed.
# Disclaimer: this software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.

# python imports
from unittest import TestCase, main
from httplib import HTTPConnection
from json import dumps, loads


class TestRegression(TestCase):

    def setUp(self):
        self.ip = "10.0.200.231"
        self.port = "6161"
        self.headers = {'Content-Type': 'application/json',
                        'Accept': 'application/json'}
        self.timeout = 10
        # connect
        self.conn = HTTPConnection(self.ip, self.port, timeout=self.timeout)

    def tearDown(self):
        self.conn.close()

    def test_1_basic_request(self):
        """
        """

        # request an pa computation
        path = "/5gt/so/v1/PAComp"
        data = {
            "ReqId": "string",
            "NFVI": {
                "resource_types": [
                    "string"
                ],
                "NFVIPoPs": [
                    {
                        "Id": "DC1",
                        "gw_ip_address": "172.16.102.116",
                        "capabilities": {
                            "cpu": 500,
                            "ram": 2400,
                            "storage": 135000
                        },
                        "availableCapabilities": {
                            "cpu": 500,
                            "ram": 2400,
                            "storage": 135000
                        },
                        "internal_latency": 1.04
                    },
                    {
                        "Id": "DC2",
                        "gw_ip_address": "172.16.102.117",
                        "capabilities": {
                            "cpu": 40,
                            "ram": 160,
                            "storage": 7000
                        },
                        "availableCapabilities": {
                            "cpu": 40,
                            "ram": 160,
                            "storage": 7000
                        },
                        "internal_latency": 4.16
                    },
                    {
                        "Id": "DC3",
                        "gw_ip_address": "172.16.102.118",
                        "capabilities": {
                            "cpu": 40,
                            "ram": 160,
                            "storage": 7000
                        },
                        "availableCapabilities": {
                            "cpu": 40,
                            "ram": 160,
                            "storage": 7000
                        },
                        "internal_latency": 4.16
                    }
                ],
                "LLs": [
                    {
                        "LLid": "LL1",
                        "capacity": {
                            "total": 1250000000,
                            "available": 12500000
                        },
                        "delay": 3.3,
                        "length": 250,
                        "src": {
                            "idSrc": "DC1",
                            "gwIPSrc": "172.16.102.116"
                        },
                        "dst": {
                            "idDst": "DC2",
                            "gwIPDst": "172.16.102.117"
                        }
                    },
                    {
                        "LLid": "LL2",
                        "capacity": {
                            "total": 1250000000,
                            "available": 12500000
                        },
                        "delay": 1.3,
                        "length": 150,
                        "src": {
                            "idSrc": "DC1",
                            "gwIPSrc": "172.16.102.116"
                        },
                        "dst": {
                            "idDst": "DC3",
                            "gwIPDst": "172.16.102.118"
                        }
                    }
                ]
            },
            "NSD": {
                "Id": "Req1",
                "name": "req1",
                "VNFs": [
                    {
                        "vnfId": "VNFa",
                        "instancesSRC": 2,
                        "instancesDST": 3,
                        "requirements": {
                            "cpu": 3,
                            "ram": 8,
                            "storage": 1
                        }
                    }
                ],
                "VNFLinks": [
                    {
                        "src": "172.16.102.116",
                        "required_capacity": 12500000
                    }
                ],
                "max_latency": 9.6
            },
            "callback": "http://localhost:8080/5gt/so/v1/ns"
        }
        self.conn.request("POST", path, dumps(data), self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        data = rsp.read()
        self.assertEqual(rsp.status, 200)


if __name__ == '__main__':
    main()
