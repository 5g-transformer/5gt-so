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
        self.ip = "localhost"
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
  "nfvi": {
    "resource_types": [
      "cpu",
      "ram",
      "storage",
      "bandwidth"
    ],
    "NFVIPoPs": [
      {
        "id": "A",
        "location": {
                                "center": {
            "longitude": 10.878099,
            "latitude": 1.9921979
          },
          "radius": 0
                  },
      
        "gw_ip_address": "10.10.10.1",
        "capabilities": {
          "cpu": 100,
          "ram": 100,
          "storage": 100,
          "bandwidth": 100,
          "mac":True
        },
        "availableCapabilities": {
          "cpu": 100,
          "ram": 100,
          "storage": 100,
          "bandwidth": 100
        },
        "failure_rate": 0,
        "internal_latency": 2.5
      },
      {
        "id": "B",
        "location": {
          "center": {
            "longitude": 4.878099,
            "latitude": 31.9921979
          },
          "radius": 0
        },
        "gw_ip_address": "10.10.10.3",
        "capabilities": {
          "cpu": 100,
          "ram": 100,
          "storage": 100,
          "bandwidth": 100,
          "mec":True
        },
        "availableCapabilities": {
          "cpu": 100,
          "ram": 100,
          "storage": 100,
          "bandwidth": 100
        },
        "failure_rate": 0,
        "internal_latency": 3.3
      },
      {
        "id": "C",
        "location": {
          "center": {
            "longitude": -3.878099,
            "latitude": 44.9921979
          },
          "radius": 0
        },
        "gw_ip_address": "10.10.10.5",
        "capabilities": {
          "cpu": 100,
          "ram": 100,
          "storage": 100,
          "bandwidth": 100
        },
        "availableCapabilities": {
          "cpu": 100,
          "ram": 100,
          "storage": 100,
          "bandwidth": 100
        },
        "failure_rate": 0,
        "internal_latency": 4.04
      },
      {
        "id": "D",
        "location": {
          "center": {
            "longitude": 5.1426034,
            "latitude": 22.0306169
          },
          "radius": 0
        },
        "gw_ip_address": "10.10.10.7",
        "capabilities": {
          "cpu": 100,
          "ram": 100,
          "storage": 100,
          "bandwidth": 100
        },
        "availableCapabilities": {
          "cpu": 100,
          "ram": 100,
          "storage": 100,
          "bandwidth": 100
        },
        "failure_rate": 0,
        "internal_latency": 2.3
      }
    ],
    "LLs": [
      {
        "LLid": "A-B-1",
        "capacity": {
          "total": 40,
          "available": 40
        },
        "delay": 9,
        "source": {
          "id": "A",
          "GwIpAddress": "10.10.10.1"
        },
        "destination": {
          "id": "B",
          "GwIpAddress": "10.10.10.3"
        }
      },
      {
        "LLid": "A-B-2",
        "capacity": {
          "total": 80,
          "available": 80
        },
        "delay": 5,
        "source": {
          "id": "A",
          "GwIpAddress": "10.10.10.1"
        },
        "destination": {
          "id": "B",
          "GwIpAddress": "10.10.10.3"
        }
      },
      {
        "LLid": "A-D-1",
        "capacity": {
          "total": 50,
          "available": 50
        },
        "delay": 12,
        "source": {
          "id": "A",
          "GwIpAddress": "10.10.10.1"
        },
        "destination": {
          "id": "D",
          "GwIpAddress": "10.10.10.7"
        }
      },
      {
        "LLid": "C-D-1",
        "capacity": {
          "total": 50,
          "available": 50
        },
        "delay": 11,
        "source": {
          "id": "C",
          "GwIpAddress": "10.10.10.5"
        },
        "destination": {
          "id": "D",
          "GwIpAddress": "10.10.10.7"
        }
      },
      {
        "LLid": "C-A-1",
        "capacity": {
          "total": 35,
          "available": 55
        },
        "delay": 3,
        "source": {
          "id": "C",
          "GwIpAddress": "10.10.10.5"
        },
        "destination": {
          "id": "A",
          "GwIpAddress": "10.10.10.1"
        }
      },
      {
        "LLid": "B-A-1",
        "capacity": {
          "total": 15,
          "available": 45
        },
        "delay": 12,
        "source": {
          "id": "B",
          "GwIpAddress": "10.10.10.3"
        },
        "destination": {
          "id": "A",
          "GwIpAddress": "10.10.10.1"
        }
      },
      {
        "LLid": "C-B-1",
        "capacity": {
          "total": 20,
          "available": 20
        },
        "delay": 5,
        "source": {
          "id": "C",
          "GwIpAddress": "10.10.10.5"
        },
        "destination": {
          "id": "B",
          "GwIpAddress": "10.10.10.3"
        }
      },
      {
        "LLid": "B-C-1",
        "capacity": {
          "total": 10,
          "available": 60
        },
        "delay": 7,
        "source": {
          "id": "B",
          "GwIpAddress": "10.10.10.3"
        },
        "destination": {
          "id": "C",
          "GwIpAddress": "10.10.10.5"
        }
        },
      {
        "LLid": "B-D-1",
        "capacity": {
          "total": 10,
          "available": 70
        },
        "delay": 7,
        "source": {
          "id": "B",
          "GwIpAddress": "10.10.10.3"
        },
        "destination": {
          "id": "D",
          "GwIpAddress": "10.10.10.7"
        }
        },
      {
        "LLid": "D-C-1",
        "capacity": {
          "total": 50,
          "available": 50
        },
        "delay": 7,
        "source": {
          "id": "D",
          "GwIpAddress": "10.10.10.7"
        },
        "destination": {
          "id": "C",
          "GwIpAddress": "10.10.10.5"
        }
        },
      {
        "LLid": "D-A-1",
        "capacity": {
          "total": 50,
          "available": 50
        },
        "delay": 7,
        "source": {
          "id": "D",
          "GwIpAddress": "10.10.10.7"
        },
        "destination": {
          "id": "A",
          "GwIpAddress": "10.10.10.1"
        }

      },
      {
        "LLid": "D-B-1",
        "capacity": {
          "total": 45,
          "available": 45
        },
        "delay": 3,
        "source": {
          "id": "D",
          "GwIpAddress": "10.10.10.7"
        },
        "destination": {
          "id": "B",
          "GwIpAddress": "10.10.10.3"
        }
        }
    ]
  },
  "nsd": {
    "id": "rel1-nsd-test",
    "name": "multi-graph-ns",
    "SAP": [
                    {
                        "CPid": "CP1",
                        "location": {
                          "center": {
                            "longitude": -1.0769422,
                            "latitude": 39.1398602
                          },
                          "radius": 20
                        }
                    }
                ],
    "VNFs": [
      {
        "VNFid": "v1",
        "instances": 1,
        "requirements": {
          "cpu": 1,
          "ram": 100,
          "storage": 1
        },
        "failure_rate": 0,
        "processing_latency": 0,
        "CP": [
            {
                "cpId": "CP1"
            },
            {
                "cpId": "CP2",
                "VNFLink": {
                    "id": "v1-v2-1",
                    "latency": 12,
                    "required_capacity": 30,
                    "traversal_probability": 0
                }
            },
            {
                "cpId": "CP4",
                "VNFLink": {
                    "id": "v1-v2-0",
                    "latency": 12,
                    "required_capacity": 10,
                    "traversal_probability": 0
                }
            },
            {
                "cpId": "CP3",
                "VNFLink": {
                    "id": "v1-v4-0",
                    "latency": 28,
                    "required_capacity": 5,
                    "traversal_probability": 0
                }
            }
        ]
      },
      {
        "VNFid": "v2",
        "instances": 1,
        "requirements": {
          "cpu": 1,
          "ram": 100,
          "storage": 1
        },
        "failure_rate": 0,
        "processing_latency": 0,
        "CP": [
            {
                "cpId": "CP5",
                "VNFLink": {
                    "id": "v1-v2-0",
                    "latency": 12,
                    "required_capacity": 10,
                    "traversal_probability": 0
                }
            },
            {
                "cpId": "CP6",
                "VNFLink": {
                    "id": "v1-v2-1",
                    "latency": 12,
                    "required_capacity": 30,
                    "traversal_probability": 0
                }
            },
            {
                "cpId": "CP7",
                "VNFLink": {
                    "id": "v2-v3-0",
                    "latency": 12,
                    "required_capacity": 20,
                    "traversal_probability": 0
                }
            }
        ]
      },
      {
        "VNFid": "v3",
        "instances": 1,
        "requirements": {
          "cpu": 1,
          "ram": 1,
          "storage": 1
        },
        "failure_rate": 0,
        "processing_latency": 0,
        "CP": [
            {
                "cpId": "CP8",
                "VNFLink": {
                    "id": "v2-v3-0",
                    "latency": 12,
                    "required_capacity": 20,
                    "traversal_probability": 0
                }
            },
            {
                "cpId": "CP9",
                "VNFLink": {
                    "id": "v3-v4-0",
                    "latency": 40,
                    "required_capacity": 10,
                    "traversal_probability": 0
                }
            }
        ]
      },
      {
        "VNFid": "v4",
        "instances": 1,
        "requirements": {
          "cpu": 1,
          "ram": 1,
          "storage": 1,
          "mec":True
        },
        "failure_rate": 0,
        "processing_latency": 0,
        "CP": [
            {
                "cpId": "CP10",
                "VNFLink": {
                    "id": "v3-v4-0",
                    "latency": 40,
                    "required_capacity": 10,
                    "traversal_probability": 0
                }
            },
            {
                "cpId": "CP11",
                "VNFLink": {
                    "id": "v1-v4-0",
                    "latency": 28,
                    "required_capacity": 5,
                    "traversal_probability": 0
                }
            }
        ]
      }
    ],
    "VNFLinks": [
      {
        "id": "v1-v2-0",
        "latency": 12,
        "required_capacity": 10,
        "traversal_probability": 0
      },
      {
        "id": "v1-v2-1",
        "latency": 12,
        "required_capacity": 30,
        "traversal_probability": 0
      },
      {
        "id": "v2-v3-0",
        "latency": 12,
        "required_capacity": 20,
        "traversal_probability": 0
      },
      {
        "id": "v3-v4-0",
        "latency": 40,
        "required_capacity": 10,
        "traversal_probability": 0
      },
      {
        "id": "v1-v4-0",
        "latency": 28,
        "required_capacity": 5,
        "traversal_probability": 0
      }
    ],
    "max_latency": 100,
    "target_availability": 0,
    "max_cost": 0
  },
  "callback": "string"
}

        self.conn.request("POST", path, dumps(data), self.headers)
        self.conn.sock.settimeout(self.timeout)
        rsp = self.conn.getresponse()
        data = rsp.read()
        self.assertEqual(rsp.status, 201)


if __name__ == '__main__':
    main()
