import sys, os
import re
import argparse
import json
import uuid
from http.client import HTTPConnection
import unittest
from functools import reduce

sys.path.append(os.path.join(os.path.dirname(__file__), '../../5GT-SO'))
from sm.rooe.rooe import instantiate_ns, extract_nsd_info_for_pa, parse_resources_for_pa, amending_pa_output


########### SERVER PARAMETERS ###########
# POLITO UC3M parameters
## HOW PARAMETERS SHOULD BE SET PROPERLY
## polito_uc3m_pa_ip = "192.168.56.101"
## polito_uc3m_pa_port = 6262
## polito_uc3m_pa_uri = "/5gt/so/v2/PAComp"
polito_uc3m_pa_ip = "127.0.0.1"
polito_uc3m_pa_port = 6161
polito_uc3m_pa_uri = "/5gt/so/v1/PAComp"
# SSSA parameters
sssa_pa_ip = "127.0.0.1"
sssa_pa_port = 6161
sssa_pa_uri = "/5gt/so/v1/PAComp"
# eurecom parameters
eurecom_pa_ip = "127.0.0.1"
eurecom_pa_port = 6161
eurecom_pa_uri = "/5gt/so/v1/PAComp"


class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

    def keys(self):
        return self.__dict__.keys()


class TestVCDN(unittest.TestCase):
    VCDN_NSD_PATH = os.path.join(os.path.dirname(__file__),
                                 'r2-nsds/pa_nsd_cdn.json')
    VCDN_VNFDS_PATH = os.path.join(os.path.dirname(__file__),
                                   'r2-nsds/pa_vnfds_cdn.json')
    RESOURCES_PATH = os.path.join(os.path.dirname(__file__),
                                  'r2-nsds/pa_mtp_resources.json')
    

    def setUp(self):
        # Read NSDs and VNFDs
        with open(TestVCDN.VCDN_NSD_PATH) as f:
            self.nsd = json.load(f)
        with open(TestVCDN.VCDN_VNFDS_PATH) as f:
            self.vnfds = json.load(f)
        with open(TestVCDN.RESOURCES_PATH) as f:
            self.resources = json.load(f)

        self.uc3m = {'lat': 40.3325323, 'lon': -3.7675058}
        self.cttc = {'lat': 41.27504, 'lon': 1.987709}



    def __gen_mec_and_location(self):
        # Put NFVI PoP 2 in UC3M and NFVI PoP 1 in CTTC
        for i in range(len(self.resources['NfviPops'])):
            nfvi_pop = self.resources['NfviPops'][i]
            if nfvi_pop['nfviPopAttributes']['vimId'] == "2":
                self.resources['NfviPops'][i]['nfviPopAttributes']\
['geographicalLocationInfo'] = '({},{})'.format(self.uc3m['lat'],
                                                self.uc3m['lon'])
            elif nfvi_pop['nfviPopAttributes']['vimId'] == "1":
                self.resources['NfviPops'][i]['nfviPopAttributes']\
['geographicalLocationInfo'] = '({},{})'.format(self.cttc['lat'],
                                                self.cttc['lon'])


        # SAP related constraints, video to UC3M, mgt to CTTC
        body = Bunch(
            flavour_id='df_vCDN',
            ns_instantiation_level_id='il_vCDN_small',
            sapData=[Bunch(
                sapdId='videoSap',
                sapName='videoSap',
                description='SAP to access CDN video',
                locationInfo={
                    'center': {
                        'latitude': self.uc3m['lat'],
                        'longitude': self.uc3m['lon'],
                        'description': 'UC3M location'
                    },
                    'radius': 10
                }
            ), Bunch(
                sapdId='mgtSap',
                sapName='mgtSap',
                description='SAP to access management network',
                locationInfo={
                    'center': {
                        'latitude': self.cttc['lat'],
                        'longitude': self.cttc['lon'],
                        'description': 'CTTC location'
                    },
                    'radius': 10
                }
            )]
        )

        # Interact with the ROOE to build up the API NSD
        nsd_info = extract_nsd_info_for_pa(self.nsd, self.vnfds, body)
        resources_info = parse_resources_for_pa(self.resources, self.vnfds.keys())

        # Impose a delay of 5 for the VideoDistribution and mgt VLs
        low_latency_vls = ['mgt', 'VideoDistribution']
        for i in range(len(nsd_info['nsd']['VNFLinks'])):
            if nsd_info['nsd']['VNFLinks'][i]['id'] in low_latency_vls:
                nsd_info['nsd']['VNFLinks'][i]['latency'] = 5

        # generate request id
        reqId = str(uuid.uuid4())
        
        # put together the body of the request (cb is ignored anyway)
        body_pa = {
            "ReqId": reqId,
            "nfvi": resources_info,
            "callback": "http://localhost:8080/5gt/so/v1/__callbacks/pa/" + reqId
        }
        body_pa.update(nsd_info)
        header = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        return body_pa, header


    def __test_mec_location(self, pa_ip, pa_port, pa_uri):
        """
        Here we test that video distribution SAP is deployed in NFVIPoP 2
        mgmt SAP is deployed in NFVI PoP 1. Both deployments imposed with
        location constraints. Then the webserver must be deployed in the NFVI
        PoP 2. As well spr1 must be co-located with mgmt SAP. Such restriction
        is achieved by imposing a delay between them lower than the LL
        connecting NFVI PoP 1 and NFVI PoP 2.
        Finally, the video data link must be over the LL. To do so, we impose
        spr21 to be inside NFVI PoP 2 imposing a low delay for the VL that
        connects it with the webserver.

        If the test is passed, the placement algorithm shows that it can deal
        with:
          + multi NFVI PoP deployments
          + MEC constraints
          + location constraints

        return: body, header of the HTTP request
        """
        
        body_pa, header = self.__gen_mec_and_location()
        placement_info = {}

        conn = HTTPConnection(pa_ip, pa_port)
        conn.request("POST", pa_uri, json.dumps(body_pa), header)

        # ask pa to calculate the placement - read response and close connection
        rsp = conn.getresponse()
        placement_info = rsp.read().decode('utf-8')
        placement_info = json.loads(placement_info)

        ################
        # ASSSERTIONS ##
        ################

        # Check that video data VL is in a LL
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'VideoData' in m['mappedVLs'],
                placement_info['usedLLs'])))

        # Check that video data VL is inside UC3M
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'VideoDistribution' in m['mappedVLs'],
                filter(lambda m: m['NFVIPoP'] == '2',
                    placement_info['usedVLs']))))

        # Check that mgt VL is inside CTTC
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'mgt' in m['mappedVLs'],
                filter(lambda m: m['NFVIPoP'] == '1',
                    placement_info['usedVLs']))))

        # Check that the webserver is in the UC3M host
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'webserver' in m['mappedVNFs'],
                filter(lambda m: m['NFVIPoPID'] == '2',
                    placement_info['usedNFVIPops']))))

        # Check that the spr1 is inside CTTC host
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'spr1' in m['mappedVNFs'],
                filter(lambda m: m['NFVIPoPID'] == '1',
                    placement_info['usedNFVIPops']))))


    def test_polito_uc3m_mec_location(self):
        self.__test_mec_location(polito_uc3m_pa_ip, polito_uc3m_pa_port,
                                 polito_uc3m_pa_uri)

    def test_sssa_mec_location(self):
        self.__test_mec_location(sssa_pa_ip, sssa_pa_port, sssa_pa_uri)

    def test_eurecom_mec_location(self):
        self.__test_mec_location(eurecom_pa_ip, eurecom_pa_port, eurecom_pa_uri)


    def __gen_dettached_video_sap(self):
        # Put NFVI PoP 2 in UC3M and NFVI PoP 1 in CTTC
        for i in range(len(self.resources['NfviPops'])):
            nfvi_pop = self.resources['NfviPops'][i]
            if nfvi_pop['nfviPopAttributes']['vimId'] == "2":
                self.resources['NfviPops'][i]['nfviPopAttributes']\
['geographicalLocationInfo'] = '({},{})'.format(self.uc3m['lat'],
                                                self.uc3m['lon'])
            elif nfvi_pop['nfviPopAttributes']['vimId'] == "1":
                self.resources['NfviPops'][i]['nfviPopAttributes']\
['geographicalLocationInfo'] = '({},{})'.format(self.cttc['lat'],
                                                self.cttc['lon'])


        # SAP related constraints, video to UC3M, mgt to CTTC
        body = Bunch(
            flavour_id='df_vCDN',
            ns_instantiation_level_id='il_vCDN_small',
            sapData=[Bunch(
                sapdId='videoSap',
                sapName='videoSap',
                description='SAP to access CDN video',
                locationInfo={
                    'center': {
                        'latitude': self.uc3m['lat'],
                        'longitude': self.uc3m['lon'],
                        'description': 'UC3M location'
                    },
                    'radius': 10
                }
            ), Bunch(
                sapdId='mgtSap',
                sapName='mgtSap',
                description='SAP to access management network',
                locationInfo={
                    'center': {
                        'latitude': self.cttc['lat'],
                        'longitude': self.cttc['lon'],
                        'description': 'CTTC location'
                    },
                    'radius': 10
                }
            )]
        )

        # Interact with the ROOE to build up the API NSD
        nsd_info = extract_nsd_info_for_pa(self.nsd, self.vnfds, body)
        resources_info = parse_resources_for_pa(self.resources, self.vnfds.keys())

        # Impose a delay of 5 for the videoData and mgt VLs
        low_latency_vls = ['VideoData', 'VideoDistribution']
        for i in range(len(nsd_info['nsd']['VNFLinks'])):
            if nsd_info['nsd']['VNFLinks'][i]['id'] in low_latency_vls:
                nsd_info['nsd']['VNFLinks'][i]['latency'] = 5

        # generate request id
        reqId = str(uuid.uuid4())
        
        # put together the body of the request (cb is ignored anyway)
        body_pa = {
            "ReqId": reqId,
            "nfvi": resources_info,
            "callback": "http://localhost:8080/5gt/so/v1/__callbacks/pa/" + reqId
        }
        body_pa.update(nsd_info)
        header = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        return body_pa, header


    def __test_dettached_video_sap(self, pa_ip, pa_port, pa_uri):
        """
        Here we test that the mgt SAP is located at NFVI PoP 1, but the rest
        of the NS is deployed at NFVI PoP 2. Such behaviour is achieved
        imposing that video Distribution SAP is located at NFVI PoP2, and
        low delays for the videoData and videoDistribution VLs, so every VNF is
        in NFVI PoP 2 co-located with the video distribution SAP.

        The test checks:
         + location constraints
         + dettached SAPs assignment

        return: body, header of the HTTP request
        """
        
        body_pa, header = self.__gen_dettached_video_sap()
        placement_info = {}

        conn = HTTPConnection(pa_ip, pa_port)
        conn.request("POST", pa_uri, json.dumps(body_pa), header)

        # ask pa to calculate the placement - read response and close connection
        rsp = conn.getresponse()
        placement_info = rsp.read().decode('utf-8')
        placement_info = json.loads(placement_info)

        ################
        # ASSSERTIONS ##
        ################

        # Check that mgt VL is in a LL
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'mgt' in m['mappedVLs'],
                placement_info['usedLLs'])))

        # Check that video data VL is inside UC3M
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'VideoDistribution' in m['mappedVLs'],
                filter(lambda m: m['NFVIPoP'] == '2',
                    placement_info['usedVLs']))))

        # Check that videDistribution VL is inside CTTC
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'VideoDistribution' in m['mappedVLs'],
                filter(lambda m: m['NFVIPoP'] == '2',
                    placement_info['usedVLs']))))

        # Check that the webserver is in the UC3M host
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'webserver' in m['mappedVNFs'],
                filter(lambda m: m['NFVIPoPID'] == '2',
                    placement_info['usedNFVIPops']))))

        # Check that the spr21 is inside UC3M host
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'spr21' in m['mappedVNFs'],
                filter(lambda m: m['NFVIPoPID'] == '2',
                    placement_info['usedNFVIPops']))))

        # Check that the spr1 is inside UC3M host
        self.assertTrue(reduce(lambda a,b: a or b,
            map(lambda m: 'spr1' in m['mappedVNFs'],
                filter(lambda m: m['NFVIPoPID'] == '2',
                    placement_info['usedNFVIPops']))))


    def test_polito_uc3m_dettached_video_sap(self):
        self.__test_dettached_video_sap(polito_uc3m_pa_ip, polito_uc3m_pa_port,
                                        polito_uc3m_pa_uri)

    def test_sssa_dettached_video_sap(self):
        self.__test_dettached_video_sap(sssa_pa_ip, sssa_pa_port,
                                        sssa_pa_uri)

    def test_eurecom_dettached_video_sap(self):
        self.__test_dettached_video_sap(eurecom_pa_ip, eurecom_pa_port,
                                        eurecom_pa_uri)


if __name__ == '__main__':
    unittest.main()

