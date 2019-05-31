import sys, os
import re
import argparse
import json
import uuid
from http.client import HTTPConnection

sys.path.append(os.path.join(os.path.dirname(__file__), '../../5GT-SO'))
from sm.rooe.rooe import instantiate_ns, extract_nsd_info_for_pa, parse_resources_for_pa, amending_pa_output

class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

if __name__ == '__main__':
    # Parse args
    parser = argparse.ArgumentParser(
        description='Script to test the NSD to PA API translation')
    parser.add_argument('pa', choices=['polito_uc3m','sssa','eurecom'],
                        help='placement algorithm to invoke after translate')
    parser.add_argument('nsd', type=str, help='path to NSD')
    parser.add_argument('vnfds', type=str, help='path to the VNFDs file')
    parser.add_argument('resources', type=str, help='path to the MTP resources file')
    args = parser.parse_args()

    # TODO - translate NSD to PA request
    with open(args.nsd) as d:
        nsd = json.load(d)
    with open(args.vnfds) as f:
        vnfds = json.load(f)
    with open(args.resources) as f:
        resources = json.load(f)

    body = Bunch(
        flavour_id='df_vCDN' if re.search('CDN', args.nsd, re.IGNORECASE)\
                             else 'eHealth-vEPC_df',
        ns_instantiation_level_id='il_vCDN_small' if re.search('CDN',
                                                        args.nsd, re.IGNORECASE)\
                                    else 'eHealth-vEPC_il_default'
    )

    pa_info = extract_nsd_info_for_pa(nsd, vnfds, body)
    pa_resources = parse_resources_for_pa(resources, vnfds.keys())


    # Execute the selected PA with the translated NSD
    if args.pa == 'polito_uc3m':
        pa_ip = "127.0.0.1"
        pa_port = 6161
        pa_uri = "/5gt/so/v1/PAComp"
    elif args.pa == 'sssa':
        pa_ip = "127.0.0.1"
        pa_port = 6161
        pa_uri = "/5gt/so/v1/PAComp"
    elif args.pa == 'eurecom':
        pa_ip = "127.0.0.1"
        pa_port = 6161
        pa_uri = "/5gt/so/v1/PAComp"

    # generate request id
    reqId = str(uuid.uuid4())
    
    # put together the body of the request (cb is ignored anyway)
    body_pa = {"ReqId": reqId,
               "nfvi": pa_resources,
               "callback": "http://localhost:8080/5gt/so/v1/__callbacks/pa/" + reqId}
    body_pa.update(pa_info)
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    placement_info = {}

    try:
        conn = HTTPConnection(pa_ip, pa_port)
        conn.request("POST", pa_uri, json.dumps(body_pa), header)

        # ask pa to calculate the placement - read response and close connection
        rsp = conn.getresponse()
        if rsp.getcode() >= 400:
          print(rsp.read().decode('utf-8'))
        else:
          placement_info = rsp.read().decode('utf-8')
          placement_info = json.loads(placement_info)
          placement_info = amending_pa_output(pa_info["nsd"], placement_info)
          print(placement_info)
        conn.close()
    except ConnectionRefusedError:
        pass

