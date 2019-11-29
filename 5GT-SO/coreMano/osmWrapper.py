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
from random import randint
from six.moves.configparser import RawConfigParser
from http.client import HTTPConnection
from http.client import HTTPException
from json import dumps, load, loads
from http.client import HTTPSConnection
import requests
import time
import sys
import ssl
import os
import shutil
import netaddr

# project imports
# from coreMano.osm_db import osm_db
from nbi import log_queue, upload_folder
from db.nsir_db import nsir_db
# nothing to append since the code is executed in the folder
from swagger_server.webserver_utils import ifa014_conversion, ifa011_conversion, create_osm_files

# osm imports
from osmclient.client import Client as client
from osmclient.common.exceptions import ClientException
from osmclient.common.exceptions import NotFound


# load mtp properties
config = RawConfigParser()
config.read("../../mtp.properties")
mtp_ip = config.get("MTP", "mtp.ip")
mtp_port = config.get("MTP", "mtp.port")
mtp_path = config.get("MTP", "mtp.base_path")
# load mon properties
config.read("../../monitoring/monitoring.properties")
mon_ip = config.get("MONITORING", "monitoring.ip")


########################################################################################################################
# PRIVATE METHODS COMPUTE                                                                                              #
########################################################################################################################


def extract_sap_info (config, nsr_info, ns_descriptor):
    #nsr = {"sapInfo": {"mgtSap": "", 
    #                  "videoSap": ""}, 
    #       "deployment_id": "",
    #       "metadata": {}
    #      }
    nsr = {"sapInfo":{},
           "deployment_id": "",
           "metadata": {}
          }
    nsr["deployment_id"] = nsr_info["ns_name"]
    for sap in ns_descriptor["nsd"]["sapd"]:
        # log_queue.put(["DEBUG", "the SAPD in OSMWrapper is: %s"% (sap)])
        if (sap["addressData"][0]["floatingIpActivated"] == True):
            # log_queue.put(["DEBUG", "the SAPD with floatingIP is: %s"% (sap["cpdId"])])
            sap_descriptor = {}
            sap_descriptor[sap["cpdId"]] = []
            for vnf in config["floating_ips"].keys():
                # log_queue.put(["DEBUG", "en OSM wrapper extract_sap_info vnf is: %s" % vnf])
                # log_queue.put(["DEBUG", "en OSM wrapper extract_sap_info el link is: %s" % config["floating_ips"][vnf]["vlds"]])
                for vld in config["floating_ips"][vnf]["vlds"]:
                    sap_name = sap["nsVirtualLinkDescId"]
                    if (config['mapping']):
                        for key in config['mapping'].keys():
                            if (key == sap["nsVirtualLinkDescId"]):
                                dash = config['mapping'][key].find('_')
                                sap_name = config['mapping'][key][dash+1:]                    
                                if (vld.find("fgt") !=-1):
                                    # it means, it comes from a previously instantiated service
                                    sap_name = config['mapping'][key]
                                else:
                                    dash = config['mapping'][key].find('_')
                                    sap_name = config['mapping'][key][dash+1:]                    
                    if (vld == sap_name):
                        for elem in nsr_info['vnfs']:
                            for ip in elem['floating_ips']:
                                for ip_value in ip.keys():
                                    if (ip_value == vnf):
                                        sap_descriptor[sap["cpdId"]].append({ip_value: ip[ip_value]})
            nsr["sapInfo"].update(sap_descriptor)
    log_queue.put(["INFO", "in OSM wrapper the info of extract sap is: %s"% (nsr)])       
    return nsr

def get_information_of_scaled_service_osm(nsi_id, placement_info, osmclient):
    # this function assumes that the scaled vnfs will be in the same pop as the original one
    # example of placement_info: {"usedNFVIPops": [{"NFVIPoPID": "1", "mappedVNFs": ["webserver", "spr1", "spr21"]}]}
    ns_show = osmclient.ns.get(nsi_id)
    vim_info = get_vim_info()
    service_vnf_info = list()
    vnfs_to_request = {}
    vims = []
    # the idea is to ask for all of them and then compare with the available one to see what is needed to be created or destroyed
    # print (ns_show["constituent-vnfr-ref"])
    for elem in ns_show["constituent-vnfr-ref"]:
        vnfd_info = osmclient.vnf.get(elem)
        for vdur in vnfd_info["vdur"]:
            port_info = []
            name = vdur["name"].split("-")
            addresses = vdur["ip-address"].split(";")
            vnf_info = {}
            for interface in vdur["interfaces"]:
                mac_address = interface["mac-address"]
                mask = '/24'
                for vim in placement_info['usedNFVIPops']:
                   for mapped_vnf in vim["mappedVNFs"]:
                       if (name[7].find(mapped_vnf) !=-1):                       
                           vnf_info['name'] = mapped_vnf
                           for nfvipopcheck in vim_info[vim["NFVIPoPID"]]['nfvipop_info']:
                               if nfvipopcheck['nfviPopId'] == vim["NFVIPoPID"]:
                                   host = nfvipopcheck['networkConnectivityEndpoint'].split('-')[0]
                                   port = nfvipopcheck['networkConnectivityEndpoint'].split('-')[1]
                                   dc_iface = {"host": host, "port": port}
                                   break
                if (len(addresses)>1 and (interface["ip-address"] == addresses[0])):
                    # it means that there is a floating ip
                    ip_address = addresses[1]
                else:
                    # there is not floating ip
                    ip_address = interface["ip-address"]
                elem_port_info = {"ip_address": ip_address, "mask": mask, "mac_address": mac_address,
                                  "dc_iface": dc_iface}
                port_info.append(elem_port_info)
            # vnf_info = {"name": name[7], "dc": vim["NFVIPoPID"], "port_info": port_info, "instance": name[8]}  # R4
            vnf_info["dc"] = vim["NFVIPoPID"]
            vnf_info["port_info"] = port_info
            vnf_info ["instance"] =  name[8]
            if (len(addresses)>1):
              vnf_info['floating_ips'] = []
              # vnf_info['floating_ips'] = {vnf_info['name']: addresses[0]}
              vnf_info['floating_ips'].append({vnf_info['name']: addresses[0]})
            service_vnf_info.append(vnf_info)
    return {"ns_name": nsi_id, "vnfs": service_vnf_info}

def get_information_of_scaled_service_os(nsi_id, placement_info, scale_info):
    # this function assumes that the scaled vnfs will be in the same pop as the original one
    # example of placement_info: {"usedNFVIPops": [{"NFVIPoPID": "1", "mappedVNFs": ["webserver", "spr1", "spr21"]}]}
    # example of scale_info: {'scaleVnfType': 'SCALE_OUT', 'vnfIndex': '3', 'vnfName': 'spr21', 'instanceNumber': 2}
    # THIS IS USED BY OSM R6 !!!
    vim_info = get_vim_info()
    service_vnf_info = list()
    for vim in placement_info["usedNFVIPops"]:
        # print ("vim: ", vim)
        vim_ip = vim_info[vim['NFVIPoPID']]['ip']
        vim_token = vim_info[vim['NFVIPoPID']]['token']
        vim_token_catalog = vim_info[vim["NFVIPoPID"]]['token_catalog']
        if vim_token_catalog != None:
            compute_url = list(filter(lambda x: x['type'] == 'compute', vim_token_catalog))[0]['endpoints'][0]['url']
        else:
            compute_url = 'http://' + vim_ip + '/compute/v2.1'

#        openstack_info = make_request2('GET', vim_ip, 'http://' + vim_ip +
#                                                         '/compute/v2.1/servers', None, vim_token)
        openstack_info = make_request2('GET', vim_ip, compute_url + '/servers', None, vim_token)

        for vm in openstack_info["servers"]:
            if (vm["name"].find("fgt") !=-1):
                name = vm['name'].split('-')
                if (name[0].find('fgt') !=-1 ):
                    # we assume that only 5gt will create this kind of identifiers
                    ns_id = name[0] + '-' + name[1] + '-' + name[2] + '-' + name[3] + '-' + name[4] + '-' + name[5] 
                    if (nsi_id.find(ns_id) != -1): 
                        vnf_info = {}
                        # this is a VNF from the service
                        port_info = []  # list with each one of the interfaces of the vm
                        elem_port_info = []
                        identifier = vm["id"]
#                        resource_ip_mac = make_request2('GET', vim_ip, 'http://' + vim_ip +
#                                                        '/compute/v2.1/servers/' + identifier + '/os-interface',
#                                                        None, vim_token)
                        resource_ip_mac = make_request2('GET', vim_ip, compute_url + '/servers/' + identifier + '/os-interface',
                                                    None, vim_token)

                        for interface in resource_ip_mac['interfaceAttachments']:
                            mac_address = interface['mac_addr']
                            for ips in interface['fixed_ips']:
                                if (ips['ip_address'].find(':') == -1):
                                    # this is the ipv4 address that I want
                                    ip_address = ips['ip_address']
                                    mask = '/24'  # for the moment we set it by default
                            for nfvipopcheck in vim_info[vim['NFVIPoPID']]['nfvipop_info']:
                                if nfvipopcheck['nfviPopId'] == vim['NFVIPoPID']:
                                    host = nfvipopcheck['networkConnectivityEndpoint'].split('-')[0]
                                    port = nfvipopcheck['networkConnectivityEndpoint'].split('-')[1]
                                    dc_iface = {"host": host, "port": port}
                            elem_port_info = {"ip_address": ip_address, "mask": mask, "mac_address": mac_address,
                                             "dc_iface": dc_iface}
                            port_info.append(elem_port_info)
                        vnf_info = {"name": name[7], "dc": vim['NFVIPoPID'], "port_info": port_info}
                        vnf_info ["instance"] =  name[8]
                        #TO GET floaging IP information
#                        resource_floating = make_request2('GET', vim_ip, 'http://' + vim_ip +
#                                            '/compute/v2.1/servers/'+ identifier,
#                                            None, vim_token)
                        resource_floating = make_request2('GET', vim_ip, compute_url + '/servers/'+ identifier,
                                            None, vim_token)
                        floating_ips = []
                        for net in resource_floating["server"]["addresses"]:
                            for iface in resource_floating["server"]["addresses"][net]:
                                if (iface["OS-EXT-IPS:type"] == "floating") :
                                    floating_ips.append({name[7]: iface["addr"]})
                        vnf_info['floating_ips'] = floating_ips
                        service_vnf_info.append(vnf_info)
                        vnf_info ["instance"] =  name[8]
    # in theory is all information to be updated
    return {"ns_name": nsi_id, "vnfs": service_vnf_info}


def get_information_of_deployed_service_os(ns_name, placement_info, osm_release):
    # example of placement_info: [{"NFVIPoPID": "1", "mappedVNFs": ["webserver", "spr21"]}, {"NFVIPoPID": "2", "mappedVNFs": ["spr1"]}],
    # in OSMR3, machines in openstack are created with servicename.vnf_name.vnf_index.vnf_vdu
    # in OSMR4 and advance machines in openstack are created with - as separator
    vim_info = get_vim_info()
    service_vnf_info = list()
    vnfs = []
    openstack_info = {}
    # get the info of the involved vims
    for vim in placement_info:  # be careful, I am assuming there are not zones in this version. Different zones have the same "control IP"
        vim_ip = vim_info[vim["NFVIPoPID"]]['ip']
        vim_token = vim_info[vim["NFVIPoPID"]]['token']
        vim_token_catalog = vim_info[vim["NFVIPoPID"]]['token_catalog']
        if vim_token_catalog != None:
            compute_url = list(filter(lambda x: x['type'] == 'compute', vim_token_catalog))[0]['endpoints'][0]['url']
        else:
            compute_url = 'http://' + vim_ip + '/compute/v2.1'

#        openstack_info[vim["NFVIPoPID"]] = make_request2('GET', vim_ip, 'http://' + vim_ip +
#                                                         '/compute/v2.1/servers', None, vim_token)
        openstack_info[vim["NFVIPoPID"]] = make_request2('GET', vim_ip, compute_url + '/servers', None, vim_token)
        for vnf in vim["mappedVNFs"]:
            vnf_name = vnf
            for vm in openstack_info[vim["NFVIPoPID"]]["servers"]:
                # condition for OSM R3, creates the machine in openstack as: ns_name.vnf_name.vnfindex.vnf_id
                # condition for OSM R4 and next releases, creates the machine in openstack with '-' separator
                if (vm["name"].find("fgt") !=-1):
                    if (osm_release == '3'):
                        name = vm["name"].split('.')
                        vnf_name_os = name[1]
                    else:
                        name = vm["name"].split('-')
                        # OSM R5 puts the name of the vdu instead of the vnfname, different to OSMR3
                        # let's assume the name in the vdu_name is 'vnfname', 
                        name_bis = name[7]
                        vnf_name_os = name_bis
#                    if ((vm["name"].find(ns_name) != -1) and (vm["name"].find(vnf_name) != -1) ):
                    if ((vm["name"].find(ns_name) != -1) and (vnf_name == vnf_name_os) ):
                        port_info = []  # list with each one of the interfaces of the vm
                        elem_port_info = []
                        identifier = vm["id"]
#                        resource_ip_mac = make_request2('GET', vim_ip, 'http://' + vim_ip +
#                                                       '/compute/v2.1/servers/' + identifier + '/os-interface',
#                                                        None, vim_token)
                        resource_ip_mac = make_request2('GET', vim_ip, compute_url + '/servers/' + identifier + '/os-interface',
                                                    None, vim_token)

                        for interface in resource_ip_mac['interfaceAttachments']:
                            mac_address = interface['mac_addr']
                            for ips in interface['fixed_ips']:
                                if (ips['ip_address'].find(':') == -1):
                                    # this is the ipv4 address that I want
                                    ip_address = ips['ip_address']
                                    mask = '/24'  # for the moment we set it by default
                            for nfvipopcheck in vim_info[vim["NFVIPoPID"]]['nfvipop_info']:
                                if nfvipopcheck['nfviPopId'] == vim["NFVIPoPID"]:
                                    host = nfvipopcheck['networkConnectivityEndpoint'].split('-')[0]
                                    port = nfvipopcheck['networkConnectivityEndpoint'].split('-')[1]
                                    dc_iface = {"host": host, "port": port}
                            elem_port_info = {"ip_address": ip_address, "mask": mask, "mac_address": mac_address,
                                          "dc_iface": dc_iface}
                            port_info.append(elem_port_info)
                        vnf_info = {"name": vnf_name, "dc": vim["NFVIPoPID"], "port_info": port_info}  # R4
                        # TO GET floaging IP information
#                       resource_floating = make_request2('GET', vim_ip, 'http://' + vim_ip +
#                                                   '/compute/v2.1/servers/'+ identifier,
#                                                   None, vim_token)
                        resource_floating = make_request2('GET', vim_ip, compute_url + '/servers/'+ identifier,
                                               None, vim_token)

                        floating_ips = []
                        for net in resource_floating["server"]["addresses"]:
                            for iface in resource_floating["server"]["addresses"][net]:
                                if (iface["OS-EXT-IPS:type"] == "floating") :
                                    floating_ips.append({vnf_name: iface["addr"]})
                        vnf_info['floating_ips'] = floating_ips
                        service_vnf_info.append(vnf_info)
    return {"ns_name": ns_name, "vnfs": service_vnf_info}


def make_request2(operation, ip, uri, body, token):
    '''
    This method makes a request against the uri provided as param and returns the result.
    May raise HTTPException. However, this is done with requests library
    Parameters
    ----------
    operation: one of GET, POST, PUT, DELETE
    ip: string
        IP of the Openstack Controller
    uri: endpoint of the request
    token: authentication token previously provided by keystone
    Returns
    -------
    string
        Token provided by OpenStack Keystone.
    '''
    log_queue.put(["INFO", "In EECOMPUTE, make_request2"])
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json',
              'X-Auth-Token': token}
    if operation == 'GET':
        response = requests.get(uri, headers=header)
    if operation == 'POST':
        response = requests.post(uri, headers=header, data=dumps(body))
    if operation == 'PUT':
        response = requests.put(uri, headers=header, data=dumps(body)) 
    if operation == 'DELETE':
        response = requests.delete(uri, headers=header)
        return None
    return response.json()


def get_token(ip, user, password):
    '''
    This method makes an authentication requests against /identity/v3/auth/tokens and returns the token.
    May raise HTTPException.
    Parameters
    ----------
    ip: string
        IP of the Openstack Controller
    user, password : string
        User and password to authenticate against OpenStack Keystone.
    Returns
    -------
    string
        Token provided by OpenStack Keystone.
    '''

    log_queue.put(["INFO", "In EECOMPUTE, get_token"])
    uri = 'http://' + ip + '/identity/v3/auth/tokens'
    body = {'auth': {'identity': {'methods': ['password'],
                                  'password': {'user': {'name': user,
                                                        'domain': {"id": "default"},
                                                        'password': password}
                                               }
                                  }
                     }
            }
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}

    # old way
    # TODO handle exceptions to make sure connection is properly closed
    # get the connection and make the request
    # conn = HTTPConnection(ip, 80, timeout=10)
    # conn.request('POST', uri, dumps(body), header)

    # # read the response and close connection
    # rsp = conn.getresponse()
    # conn.close()
    # rsp.read()  # needed to empty buffer even if not used

    # if result is not OK, raise Exception
    # if rsp.status not in [200, 201]:
    #     raise HTTPException('Error: ' + str(rsp.status) + ', ' + rsp.reason)

    # get token from header
    # rsp_header = rsp.getheaders()
    # token = rsp_header[2][1]
    # log_queue.put(["INFO", "In EECOMPUTE, rsp_header is:"])
    # log_queue.put(["INFO", rsp_header])
    # log_queue.put(["INFO", "In EECOMPUTE, Token is:"])
    # log_queue.put(["INFO", token])
    # return token
    # new way, we need the endpoint catalog
    token_response = requests.post('http://' + ip + '/identity/v3/auth/tokens',
                                   data=dumps(body),
                                   headers=header)
    # Token is in the response headers
    token = token_response.headers['X-Subject-Token']
    log_queue.put(["INFO", "In EECOMPUTE, Token is:"])
    log_queue.put(["INFO", token])
    catalog_endpoint = None
    if 'catalog' in loads(token_response.content.decode('utf-8'))['token']:
        catalog_endpoint = loads(token_response.content.decode('utf-8'))['token']['catalog']
    catalog_endpoint = loads(token_response.content.decode('utf-8'))['token']['catalog']
    return [token, catalog_endpoint]


def get_vim_info():
    vim_info = {}
    config = RawConfigParser()
    config.optionxform = str
    config.read("../../coreMano/vim.properties")
    number_of_vims = config.getint("VIM", "number")
    for i in range(1, number_of_vims + 1):
        # this runs at the beginning we do not have to check if exists or not:   if ("VIM"+str(i)) not in self.vim_info:
        identifier = config.get(("VIM" + str(i)), "vimId")
        vim_info[identifier] = {}
        for option in config.options("VIM" + str(i)):
            if (option == 'numbernfvipop'):
                vim_info[identifier][option] = config.getint(("VIM" + str(i)), option)
                vim_info[identifier]['nfvipop_info'] = []
                for j in range(1, vim_info[identifier][option] + 1):
                    nfvipop_info = {}
                    for field in config.options("NFVIPOP_VIM" + str(i) + '_' + str(j)):
                        nfvipop_info[field] = config.get("NFVIPOP_VIM" + str(i) + '_' + str(j), field)
                    vim_info[identifier]['nfvipop_info'].append(nfvipop_info)
            else:
                vim_info[identifier][option] = config.get(("VIM" + str(i)), option)
        [token, token_catalog] = get_token(vim_info[identifier]['ip'],
                                           vim_info[identifier]['user'],
                                           vim_info[identifier]['password'])
        vim_info[identifier]['token'] = token
        vim_info[identifier]['token_catalog'] = token_catalog
        # vim_info[identifier]['token'] = get_token(vim_info[identifier]['ip'],
        #                                           vim_info[identifier]['user'],
        #                                          vim_info[identifier]['password'])
    return vim_info


########################################################################################################################
# PRIVATE METHODS NETWORK                                                                                              #
########################################################################################################################

def request_network_creation_mtp (service_id, network_name, floating_required, vim_id, extra_info=None):
    # extra_info it is for federation purposes, it contains the CIDR to be used and the addressPool to not be used
    mtp_uri = "http://" + mtp_ip + ":" + mtp_port + mtp_path + "/network_resources"
    # connect to MTP and make the request
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    # The required extra_info (CIDR and addressPool) should be passed through the typeSubnetData
    # However, the unified API of the MTP does not model this element as defined at IFA005. 
    # On the other hand,the response is modeled as defined at IFA005. We pass it as metadata
    vim_info = get_vim_info()
    metadata= [
              {
                 "key": "ServiceId",
                 "value": service_id
              },
              # {
              #    "key": "floating_required",
              #    "value": floating_required
              # },
              {
                 "key": "vimId",
                 "value": vim_id
              },
              {
                 "key": "AbstractNfviPoPId",
                 "value": vim_id
              }]

    typeSubnetData= {"resourceId": "",
                     "networkId": "",
                     "ipVersion": "ipv4",
                     "gatewayIp": "",
                     "cidr": "",
                     "isDhcpEnabled": True,
                     #"addressPool": "",
                     "addressPool": [],
                     #"metadata": []}
                     "metadata": [{
                                    "key": "ip-floating-required",
                                    "value": floating_required}]}

    if (floating_required == "True"):
        cidr = netaddr.IPNetwork(mon_ip).supernet(24)[0]
        # exgw = vim_info[vim_id]['nfvipop_info']['exgw']
        typeSubnetData["metadata"].append({"key": "mon_cidr", "value": str(cidr)})

    if (extra_info):
        # metadata.append({"key": "cidr", "value": extra_info["cidr"]})
        # metadata.append({"key": "addressPool", "value": str(extra_info["addressPool"])})
        typeSubnetData["cidr"] = extra_info["cidr"]
        # typeSubnetData["addressPool"] = str(extra_info["addressPool"])
        typeSubnetData["addressPool"] = extra_info["addressPool"]
    body = { "affinityOrAntiAffinityConstraints": "",
             "locationConstraints": "",
             "metadata": metadata,
             "networkResourceName": network_name,
             #"networkResourceType": "network",
             "networkResourceType": "subnet-vlan",
             "reservationId": "",
             "resourceGroupId": vim_id,
             "typeNetworkData": "",
             "typeNetworkPortData": "",
             "typeSubnetData": typeSubnetData
           }
    log_queue.put(["INFO", "Request from SO to MTP to create INTRAPOP network is:"])
    log_queue.put(["INFO", dumps(body, indent=4)])
    try:
        conn = HTTPConnection(mtp_ip, mtp_port)
        conn.request("POST", mtp_uri, dumps(body), header)
        rsp = conn.getresponse()
        request = rsp.read()
        request = request.decode("utf-8")
        log_queue.put(["INFO", "Answer from MTP to VIM creation is:"])
        request = loads(request)
        log_queue.put(["INFO", dumps(request, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the MTP server is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the MTP server is not running or the connection configuration is wrong"])
    # return request['networkData']['networkResourceId']
    return request

def delete_network_creation_mtp (networkResourceIds):
    mtp_uri = "http://" + mtp_ip + ":" + mtp_port + mtp_path + "/network_resources?networkResourceId="
    # connect to MTP and make the request
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    if len(networkResourceIds) == 0:
        return {}
    else:
        ids = ""
        log_queue.put(["INFO", "In delete_network_creation_mtp, networkResourcesIds: %s"%networkResourceIds])
        for x in range(0, len(networkResourceIds)):
            if (x == len(networkResourceIds) - 1):
                ids = ids + networkResourceIds[x]
            else:
                ids = ids + networkResourceIds[x] + ','
        mtp_uri = mtp_uri + ids
        try:
            conn = HTTPConnection(mtp_ip, mtp_port)
            conn.request("DELETE", mtp_uri, None, header)
            rsp = conn.getresponse()
            request = rsp.read()
            request = request.decode("utf-8")
            log_queue.put(["INFO", "Answer from MTP to VIM deletion is:"])
            request = loads(request)
            log_queue.put(["INFO", dumps(request, indent=4)])
            conn.close()
        except ConnectionRefusedError:
            # the MTP server is not running or the connection configuration is wrong
            log_queue.put(["ERROR", "the MTP server is not running or the connection configuration is wrong"])
        return request


def create_os_networks(info_to_create_networks, federatedInfo=None):
    vim_info = get_vim_info()
    log_queue.put(["INFO", "In OSM wrapper, info_to_create_networks:"])
    log_queue.put(["INFO", dumps(info_to_create_networks, indent=4)])

    created_routers= {}
    networkResourceIds = []
    cidrs = {}
    vlans = {}
    addressPool = {}
    for key in info_to_create_networks['name'].keys():
        for vim in info_to_create_networks['name'][key]:
            floating_required = "False"
            for vnf in info_to_create_networks['floating_ips'].keys():
               for vl in info_to_create_networks['floating_ips'][vnf]['vlds']:
                   if (key.find(vl) != -1 and info_to_create_networks['floating_ips'][vnf]['vimId'] == vim):
                      if not vim in created_routers:
                          created_routers[vim] = []
                      if (vl not in created_routers[vim]):
                          created_routers[vim].append(vl)
                          floating_required = "True"
            # for federation purposes
            extra_info = {}
            if (federatedInfo):
                for elem in federatedInfo['cidr'].keys():
                    if (key.find(elem) !=-1):
                        # this is the network that I am trying to get
                        extra_info["cidr"] = federatedInfo["cidr"][elem]
                        extra_info["addressPool"] = federatedInfo["addressPool"][elem]
                        break
            if not extra_info:
                extra_info = None
            request = request_network_creation_mtp (info_to_create_networks['ns_name'], key, floating_required, vim, extra_info)
            if (request): #you save the information of the networks that you really create     
                # agreement: for each request we will receive a networkResourceId element that we need for the mtp to warn about it
                networkResourceIds.append(request['networkData']['networkResourceId'])
                if not request["networkData"]["networkResourceName"] in cidrs:
                    cidrs[request["networkData"]["networkResourceName"]] = request["subnetData"]["cidr"]
                # 190828: with OSM always it will be vlan, however we check it, previous code commented
                # if not request["networkData"]["networkResourceName"] in vlans:
                #     for elem in request["subnetData"]["metadata"]:
                #         if (elem["key"] == "SegmentationID"):
                #             vlans[request["networkData"]["networkResourceName"]] = elem["value"]
                if (request["networkData"]["networkType"].find("vlan") != -1):
                    if not request["networkData"]["networkResourceName"] in vlans:
                            vlans[request["networkData"]["networkResourceName"]] = request["networkData"]["segmentType"]
                if not request["networkData"]["networkResourceName"] in addressPool:
                    addressPool[request["networkData"]["networkResourceName"]] = []
                for pool in request["subnetData"]["addressPool"]:
                    addressPool[request["networkData"]["networkResourceName"]].append(pool)
                ###### end code 190828
    info_to_create_networks['networkResourceIds'] = networkResourceIds
    info_to_create_networks['cidr'] = cidrs
    info_to_create_networks['vlan_id'] = vlans
    info_to_create_networks['addressPool'] = addressPool
    return info_to_create_networks


def delete_networks(info_to_create_networks):
    delete_network_creation_mtp(info_to_create_networks["networkResourceIds"])

def get_dhcp_agents(vim_info):
    dhcp_agents = {}
    for key in vim_info.keys():
        dhcp_agents[key] = []
        vim_ip = vim_info[key]['ip']
        vim_token = vim_info[key]['token']
        resources = make_request2('GET', vim_ip, 'http://' + vim_ip + ':9696/v2.0/agents', None, vim_token)
        for agent in resources['agents']:
            if agent['agent_type'] == 'DHCP agent':
                da = {}
                da[agent['host']] = agent['id']
                dhcp_agents[key].append(da)
    return dhcp_agents


def deploy_vls_vim(nsId, nsd_json, vnfds_json, instantiationLevel, deployment_flavour, resources, placement_info, nestedInfo=None):
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
    # save virtual links info related to nsId so it can be released at terminate
    log_queue.put(["INFO", "In OSMWrapper deploy vls vim"])
    virtual_link_vim = {}
    # in virtual_link_vim dict, there is a key for each VL in the NSD, 
    # and the value is the list of PoPs where it has to be deployed
    for vl in nsd_json["nsd"]["virtualLinkDesc"]:
        virtual_link_vim[vl["virtualLinkDescId"]] = []
    # for easier parsing, create a dict of GatewayIP-NFVIPoP
    gw_pop = {}
    for pop in resources["NfviPops"]:
        for ep in pop["nfviPopAttributes"]["networkConnectivityEndpoint"]:
            gw_pop[ep["netGwIpAddress"]] = pop["nfviPopAttributes"]["nfviPopId"]
    # for easier parsing, create a dict with LL ids as keys and the value is the list of the two NFVI PoPs it connects
    ll_pops = {}
    for LL in resources["logicalLinkInterNfviPops"]:
        LLid = LL["logicalLinks"]["logicalLinkId"]
        ll_pops[LLid] = []
        src_ip = LL["logicalLinks"]["srcGwIpAddress"]
        ll_pops[LLid].append(gw_pop[src_ip])
        dst_ip = LL["logicalLinks"]["dstGwIpAddress"]
        ll_pops[LLid].append(gw_pop[dst_ip])
    for vl in placement_info["usedVLs"]:
        for mvl in vl["mappedVLs"]:
            if not vl["NFVIPoP"] in virtual_link_vim[mvl]:
                virtual_link_vim[mvl].append(vl["NFVIPoP"])
    for ll in placement_info["usedLLs"]:
        for mvl in ll["mappedVLs"]:
            if not ll_pops[ll["LLID"]][0] in virtual_link_vim[mvl]:
                virtual_link_vim[mvl].append(ll_pops[ll["LLID"]][0])
            if not ll_pops[ll["LLID"]][1] in virtual_link_vim[mvl]:
                virtual_link_vim[mvl].append(ll_pops[ll["LLID"]][1])

    # cidr_id y vlan_id is global for all the network services
    info_to_create_networks = {'ns_name': nsId,
                               'nsd_name': nsd_json["nsd"]["nsdIdentifier"], 'name': {}, 'vlan_id': {}, 'cidr': {}, 'floating_ips': {}, 'mapping':{}, 'addressPool': {}}
    # first getting the vlds of the vnfs requiring a floating IP
    floating_ips = {}
    #first create the list of vnfs in this instantiation level and deployment flavour
    vnf_profiles = []
    vnfs = []
    for nsdf in nsd_json['nsd']['nsDf']:
        for nsil in nsdf['nsInstantiationLevel']:
            if (nsil["nsLevelId"] == instantiationLevel):
                for elem in nsil["vnfToLevelMapping"]:
                    # log_queue.put(["INFO", dumps(elem["vnfProfileId"], indent=4)])
                    vnf_profiles.append(elem["vnfProfileId"])
        if (nsdf['nsDfId'] == deployment_flavour):
            for vnf in nsdf['vnfProfile']:
                if (vnf['vnfProfileId'] in vnf_profiles):
                    vnfs.append(vnf['vnfdId'])          
    for vnf in vnfs:
        for extcpd in vnfds_json[vnf]['vnfExtCpd']:
            if (extcpd['addressData'][0]['floatingIpActivated'] == True):
                if vnf not in floating_ips:
                    floating_ips[vnf] = []
                floating_ips[vnf].append(extcpd['cpdId'])
    log_queue.put(["DEBUG", dumps(floating_ips, indent=4)])
    floating_ips2 = {}
    for nsdf in nsd_json['nsd']['nsDf']:
        if (nsdf['nsDfId'] == deployment_flavour):
            for vnf in nsdf['vnfProfile']:
                if (vnf['vnfdId'] in list(floating_ips.keys())):
                    for nsvl in vnf['nsVirtualLinkConnectivity']:
                        if (nsvl['cpdId'][0] in floating_ips[vnf['vnfdId']]):
                            for profile in nsdf['virtualLinkProfile']:
                                if (profile['virtualLinkProfileId'] == nsvl['virtualLinkProfileId']):
                                    if vnf['vnfdId'] not in floating_ips2:
                                        floating_ips2[vnf['vnfdId']] = {}
                                        floating_ips2[vnf['vnfdId']]['vlds'] = []   
                                    # adding particularization in case there is nestedInfo
                                    if (nestedInfo):
                                        nested_id = next(iter(nestedInfo))
                                        if len (nestedInfo[nested_id]) > 1: #when there is federation
                                            for vl in nestedInfo[nested_id][0]:
                                                for key in vl.keys():
                                                    if (key == profile['virtualLinkDescId']):
                                                        floating_ips2[vnf['vnfdId']]['vlds'].append(key)
                                        else:
                                            for vl in nestedInfo[nested_id][0]:
                                                for key in vl.keys(): 
                                                    if (key == profile['virtualLinkDescId']):
                                                        floating_ips2[vnf['vnfdId']]['vlds'].append(vl[key])
                                    else:
                                        floating_ips2[vnf['vnfdId']]['vlds'].append(profile['virtualLinkDescId'])
    for pop in placement_info["usedNFVIPops"]:
        for vnf in pop['mappedVNFs']:
            floating_ips2[vnf]['vimId'] = pop['NFVIPoPID']
    info_to_create_networks['floating_ips'] = floating_ips2
    ########################## to know in which networks I need to create routers to provide the floating IP
    federated_info = None
    for network in virtual_link_vim.keys():
        if len(virtual_link_vim[network]) > 0:
            network_id = nsId + '_' + network
            # composition/federation: adding particularization in case there is nestedInfo
            if (nestedInfo):
                nested_id = next(iter(nestedInfo))
                if len (nestedInfo[nested_id]) > 1:
                    # nested from a consumer domain
                    federated_info = nestedInfo[nested_id][1]["networkInfo"]
                else:
                    # nested local
                    network_id = nsId + '_' + nested_id + '_' + network
                    for vl in nestedInfo[nested_id][0]:
                        for key in vl.keys(): 
                            # log_queue.put(["DEBUG", "in deploy vim vl BBB, comparing vl: %s, with network: %s"%(key, network)])
                            if (key == network):  
                                if (vl[key].find("fgt-") !=-1):
                                    network_id = vl[key]
                                else:
                                    network_id = nsId + '_' + vl[key]
                                if key not in info_to_create_networks['mapping']:
                                    info_to_create_networks['mapping'][key] = network_id
                                break
            info_to_create_networks['name'][network_id] = virtual_link_vim[network]
    log_queue.put(["INFO", "info_to_create_networks in deploy_vls_vim is: %s"%info_to_create_networks])
    if federated_info:
        log_queue.put(["INFO", "extra info for federation in deploy_vls_vim is: %s"%federated_info])
    # in create_os_networks, depending on the answer of the MTP, we will update the info_to_create_networks structure
    info_to_create_networks = create_os_networks(info_to_create_networks, federated_info)
    log_queue.put(["INFO", "info_to_create_networks after CREATED in deploy_vls_vim is: %s"%info_to_create_networks])
    return info_to_create_networks


########################################################################################################################
# PRIVATE METHODS OSM                                                                                              #
########################################################################################################################

class OsmWrapper(object):
    """
    Class description
    """

    # Function to adapt the output of the PA algorithm to the input expected by osmclient
    def adapt_placement_to_osm(self, placement_info, nsd_name):
        log_queue.put(["INFO", "In adapt placement to osm: %s" % nsd_name])
        nsd = self.client.nsd.get(nsd_name)
        vnfs = nsd['constituent-vnfd']
        distribution = []
        for NFVIPoPId in placement_info:
            for mappedvnf in NFVIPoPId['mappedVNFs']:
                for nsd_vnf in vnfs:
                    if (mappedvnf == nsd_vnf['vnfd-id-ref']):
                        distrib = {"datacenter": NFVIPoPId['NFVIPoPID'],
                                   "member-vnf-index-ref": nsd_vnf["member-vnf-index"]}
                        distribution.append(distrib)
                        break
        return distribution

    def get_vnf_index(self, nsd_name, key):
        nsd = self.client.nsd.get(nsd_name)
        for vnf in nsd['constituent-vnfd']:
            if vnf['vnfd-id-ref'] == key:
                return vnf['member-vnf-index']
        return None

    # Create NS according to version osm ns-create2
    def create_ns(self, ns_name, nsd_name, distribution, config, ssh_keys=None):
        for ns in self.client.ns.list():
            if ns_name == ns['name']:
                #logger.debug("NS '{}' already in OSM".format(ns_name))
                return None
        try:
            log_queue.put(["INFO", "In OSM Wrapper: CREATE_NS, distrib is"])
            for c in distribution:
                log_queue.put(["INFO", dumps(c, indent=4)])
            log_queue.put(["INFO", "In OSM Wrapper: CREATE_NS, config is"])
            log_queue.put(["INFO", dumps(config, indent=4)])
            self.client.ns.create2(nsd_name, ns_name, distribution=distribution, config=config, ssh_keys=ssh_keys)
            return self.client.ns.get(ns_name)['id']
        except ClientException as inst:
            log_queue.put(["INFO", "%s" % inst.message])
            return None

    def get_osm_token(self):
        # first we need to get the token
        port = 9999
        timeout = 10
        path_token = "/osm/admin/v1/tokens"
        header_token = {'Content-Type': 'application/json'}
        try:
            conn = HTTPSConnection(self.host_ip, port, timeout= timeout, context=ssl._create_unverified_context()) 
            body = { "username": self.user,
	             "password": self.password,
	             "project": self.project
                   }
            conn.request("POST", path_token, dumps(body), header_token )
            conn.sock.settimeout(timeout)
            rsp = conn.getresponse()
            res = rsp.read()
            res = res.decode("utf-8")
            index_a = res.find('id:')
            index_b = res.find('admin')
            res_filtered = res[index_a+3:index_b-1]
            conn.close()
            token = res_filtered
            return token
        except ConnectionRefusedError:
            # the MTP server is not running or the connection configuration is wrong
            log_queue.put(["ERROR", "OSM is not running or the connection configuration is wrong"])


    # Scale NS operation
    def scale_ns_op (self, nsi_id, scaleVnfType, vnf_name, vnf_index):
        port = 9999
        timeout= 10
        resp = self.client.ns.get(nsi_id)
        try:
            conn = HTTPSConnection(self.host_ip, port, timeout= timeout, context=ssl._create_unverified_context()) 
            body = { "scaleType": "SCALE_VNF",
                     "scaleVnfData": 
                            { "scaleVnfType": scaleVnfType,
                              "scaleByStepData": {
                                  "scaling-group-descriptor": vnf_name + "_manualscale",
                                  "member-vnf-index": vnf_index
                                  }
                            }
                   }
            path_scale = "/osm/nslcm/v1/ns_instances/" + resp['id'] + "/scale"
            header_scale = {'Content-Type': 'application/json', 
                        'Accept': 'application/json',
                        'Authorization': 'Bearer %s' % self.token}

        
            conn.request("POST", path_scale, dumps(body), header_scale)
            rsp = conn.getresponse()
            data = rsp.read().decode("utf-8")
            data = loads(data)
            conn.close()
            return data['id']
        except ClientException as inst:
            log_queue.put(["INFO", "%s" % inst.message])
            return None

    # Get information of the instantiation process at OSM
    def get_status_of_deployed_service(self, ns_name, number_vnfs):
        log_queue.put(["INFO", "In OSM Wrapper, get status deployed service"])
        timeout = number_vnfs * 60  # we give 60*n seconds to launch n VM's with openstack
        start_time = time.time()
        current_time = 0
        nsr = None
        while ((current_time < timeout) and nsr == None):
            nsr = self.get_service_status(ns_name)
            if (nsr == "Failed"):
                return "Failed"
            if ( (nsr is not None) and (nsr is not "Failed") ):
                break
            current_time = time.time() - start_time
            time.sleep(5)
        return nsr

    def get_service_status(self, ns_name):
        log_queue.put(["INFO", "In OSM Wrapper, get service status"])
        resp = self.client.ns.get(ns_name)
        if self.release == "3":
            nsopdata = self.client.ns.get_opdata(resp['id'])
            nsr = nsopdata['nsr:nsr']
            if (nsr['name-ref'] == ns_name):
                if ((nsr['operational-status'] == 'running') and (nsr['config-status'] == 'configured')):
                    return resp['nsd']

                elif (nsr['operational-status'] == 'failed'):
                    return "Failed"

                else:
                    return None
        else:
            if ((resp['operational-status'] == 'running') and (resp['config-status'] == 'configured')):
                return resp['nsd']
            
            elif (resp['operational-status'] == 'failed'):
                return "Failed"

            else:
                return None

    def extract_target_il(self, body):
        if (body.scale_type == "SCALE_NS"):
            return body.scale_ns_data.scale_ns_to_level_data.ns_instantiation_level

    def extract_scaling_info(self, ns_descriptor, current_df, current_il, target_il):
        # we extract the required scaling operations comparing target_il with current_il
        # assumption 1: we assume that there will not be new VNFs, so all the keys of target and current are the same
        # scale_info: list of dicts {'vnfName': 'spr21', 'scaleVnfType': 'SCALE_OUT', 'vnfIndex': "3"}
        nsd_name = ns_descriptor["nsd"]["nsdIdentifier"] + "_" + current_df + "_" + current_il
        target_il_info = {}
        current_il_info = {}
        for df in ns_descriptor["nsd"]["nsDf"]:
            if (df["nsDfId"] == current_df):
                for il in df["nsInstantiationLevel"]:
                    if (il["nsLevelId"] == target_il):
                        for vnf in il["vnfToLevelMapping"]:
                            for profile in df["vnfProfile"]:
                                if (vnf["vnfProfileId"] == profile["vnfProfileId"]):
                                    target_il_info[profile["vnfdId"]] = int(vnf["numberOfInstances"])
                    if (il["nsLevelId"] == current_il):
                        for vnf in il["vnfToLevelMapping"]:
                             for profile in df["vnfProfile"]:
                                 if (vnf["vnfProfileId"] == profile["vnfProfileId"]):
                                     current_il_info[profile["vnfdId"]] = int(vnf["numberOfInstances"])
        log_queue.put(["DEBUG", "Target il %s info: %s"% (target_il, target_il_info)])
        log_queue.put(["DEBUG", "Current il %s info: %s"% (current_il, current_il_info)])
        scaling_il_info = []
        for key in target_il_info.keys():
            scaling_sign = target_il_info[key] - current_il_info[key]
            if (scaling_sign !=0):
                scale_info ={}
                scale_info["vnfName"] = key 
                index = self.get_vnf_index(nsd_name, key)
                if (index == None):
                    log_queue.put(["DEBUG", "problem with target il info, violating assumption 1"])
                scale_info["vnfIndex"] = index
                if (scaling_sign > 0): #SCALE_OUT
                    scale_info["scaleVnfType"] = "SCALE_OUT"
                elif (scaling_sign < 0): #SCALE_IN
                    scale_info["scaleVnfType"] = "SCALE_IN"          
                for ops in range (0, abs(scaling_sign)):
                    # scale_info["instanceNumber"] = str(current_il_info[key] + ops + 1) -> not needed instance number
                    # scaling operation are done one by one
                    # protection for scale_in operation: the final number of VNFs cannot reach 0
                    if not (scale_info["scaleVnfType"] == "SCALE_IN" and (current_il_info[key] - ops < 1) ):
                        scaling_il_info.append(scale_info)
        log_queue.put(["DEBUG", "Scale_il_info is: %s"%(scaling_il_info)])
        return scaling_il_info		

########################################################################################################################
# PUBLIC METHODS                                                                                                       #
########################################################################################################################

    def __init__(self, name, host_ip, ro_ip, release):
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
        log_queue.put(["INFO", "In OSM Wrapper"])
        self.host_ip = host_ip
        self.ro_host = ro_ip
        self.release = release
        config_mano = RawConfigParser()
        config_mano.read("../../coreMano/coreMano.properties")
        self.user = config_mano.get("OSM", "user")
        self.password = config_mano.get("OSM", "password")
        self.project = config_mano.get("OSM", "project")


        if self.release == "3":
            self.client = client(host=self.host_ip, ro_host=self.ro_host)  # init the client
        else:
            self.client = client(host=self.host_ip, sol005=True)
            self.token = ""

    def instantiate_ns(self, nsi_id, ns_descriptor, vnfds_descriptor, body, placement_info, resources, nestedInfo=None):
        """
        Instanciates the network service identified by nsi_id, according to the infomation contained in the body and
        placement info.
        Parameters
        ----------
        nsi_id: string
            identifier of the network service instance
        ns_descriptor: dict
            json containing the nsd
        config: dict
            {ns_name: 
             nsd_name:
             name: name of the network in the VIM
             vlan_id:
             cidr: 
             network_ids: {"vimId": network_id,
                           ...
                          }
             }

        body: http request body
            contains the flavour_id ns_instantiation_level_id parameters
        placement_info: dict
            result of the placement algorithm
        Returns
        -------
        To be defined
        """

        instantiationLevel = body.ns_instantiation_level_id
        deploymentFlavour = body.flavour_id
        # for composition/federation
        if nestedInfo:
            nested_descriptor = next(iter(nestedInfo))
            if len (nestedInfo[nested_descriptor]) > 1:
                # nested from a consumer domain
                nsId_tmp = nsi_id
            else:
                # nested local
                nsId_tmp = nsi_id + '_' + nested_descriptor
        else:
            nsId_tmp = nsi_id
        log_queue.put(["INFO", "*****Time measure: OSMW start create networks OSM wrapper"])
        config = deploy_vls_vim(nsi_id, ns_descriptor, vnfds_descriptor, instantiationLevel, deploymentFlavour, resources, placement_info, nestedInfo)
        nsir_db.save_vim_networks_info(nsId_tmp, config)
        # pass nsi_id as ns_name
        # for OSM R5, we have to indicate that we do not want to use wim at the client
        config['release'] = self.release
        # in osm dbs, nsds will stored under the following convention: "nsdIdentifier_instantiationlevel"
        log_queue.put(["INFO", "*****Time measure: OSMW finish create networks OSM wrapper"])
        log_queue.put(["INFO", "*****Time measure: OSMW start instantiating VNFs at OSM wrapper"])
        log_queue.put(["INFO", "In OSM Wrapper, instantiate_ns"])
        distrib = self.adapt_placement_to_osm(
            placement_info['usedNFVIPops'], ns_descriptor["nsd"]['nsdIdentifier'] + '_' + body.flavour_id + '_' + body.ns_instantiation_level_id)
        r = self.create_ns(nsId_tmp, ns_descriptor['nsd']['nsdIdentifier'] + '_' + body.flavour_id + '_' +
                           body.ns_instantiation_level_id, config=config, distribution=distrib)

        if r is not None:
            number_vnfs = len(vnfds_descriptor)
            nsr = self.get_status_of_deployed_service(nsId_tmp, number_vnfs)
            if (nsr == "Failed"):
                log_queue.put(["INFO", "In OSM Wrapper, the instantiation of the service failed"])
                # but osm needs to be cleaned
                # try:
                #    self.client.ns.delete(nsId_tmp)
                # except ClientException as inst:
                #    log_queue.put(["INFO", "%s" % inst])
                #    return None
                # time.sleep(10*number_vnfs)
                return None
            else:
                nsr_info = get_information_of_deployed_service_os(nsId_tmp, placement_info["usedNFVIPops"], config['release'])
                log_queue.put(["INFO", "In OSM Wrapper, instantiate_ns info is:"])
                log_queue.put(["INFO", dumps(nsr_info, indent=4)])
                nsir_db.save_vnf_deployed_info(nsId_tmp, nsr_info['vnfs'])
                nsr = extract_sap_info (config, nsr_info, ns_descriptor)
                # log_queue.put(["DEBUG", "In OSM Wrapper, instantiate_ns return is NSR:"])
                # log_queue.put(["DEBUG", dumps(nsr, indent=4)])
                return nsr
        else:
            return None


    def scale_ns(self, nsi_id, ns_descriptor, vnfds_descriptor, body, current_df, current_il, placement_info):
        """
        Scales the network service identified by nsi_id, according to the infomation contained in the body and current instantiation level.
        Parameters
        ----------
        nsi_id: string
            identifier of the network service instance
        ns_descriptor: dict
            json containing the nsd
        vnfds_descriptor: array 
            jsons of the vnfds
        body: dict
            scaling information
        current il: string
            identifier of the current instantiation level
        placement_info: dict
            dictionary with the placement info 
        Returns
        -------
        To be defined
        """
        if (self.release =="3"):
            return "Scaling not possible with OSM Release 3"
        target_il = self.extract_target_il(body)
        scale_ops = self.extract_scaling_info(ns_descriptor, current_df, current_il, target_il)
        # refresh the token
        self.token = self.get_osm_token() # we initialize here the token, 
        # not in init because not all the operations need a token
        for vnf in scale_ops:
            # we perform scaling operations one by one
            r= self.scale_ns_op (nsi_id, vnf['scaleVnfType'], vnf['vnfName'], vnf['vnfIndex'])
            if r is not None:
               while ( self.get_service_status(nsi_id) == None):
                   time.sleep(5)
            else:
               # there has been a failure and the scaling operation has not been processed
               return None
        log_queue.put(["DEBUG", "scaled service: %s" % nsi_id])
        # nsr_scale_info = get_information_of_scaled_service_osm(nsi_id, placement_info, self.client)
        nsr_scale_info = get_information_of_scaled_service_os(nsi_id, placement_info, self.client)
        # update nsir_db
        nsir_db.save_vnf_deployed_info(nsi_id, nsr_scale_info['vnfs'])
        config = nsir_db.get_vim_networks_info(nsi_id)
        # extract the sap
        nsr = extract_sap_info (config, nsr_scale_info, ns_descriptor)
        #remove vnfIdex from scale_ops, which is an OSM concept
        for elem in scale_ops:
            del elem['vnfIndex']
        return [nsr, scale_ops]

    def terminate_ns(self, nsi_id):
        """
        Terminates the network service identified by nsi_id.
        Parameters
        ----------
        nsi_id: string
            identifier of the network service instance
        Returns
        -------
        To be defined
        """
        vnf_info = nsir_db.get_vnf_deployed_info(nsi_id)
        number_vnfs = len(vnf_info)
        log_queue.put(["INFO", "*****Time measure: OSMW starting deleting VNFs at OSM for service: %s" %nsi_id])
        log_queue.put(["INFO", "In OSM Wrapper TERMINATE, number_vnfs: %s"%number_vnfs])
        try:
            self.client.ns.delete(nsi_id)
        except ClientException as inst:
            # log_queue.put(["INFO", "%s" % inst.message])
            log_queue.put(["INFO", "%s" % inst])
            # there is an exception and then it exists, however, VNFs are correctly deleted
            # return None

            # remove the created networks at the different vims
        # sleep to make sure all ports have been deleted by osm
        time.sleep(10*number_vnfs)
        log_queue.put(["INFO", "*****Time measure: OSMW deleted VNFs at OSM"])
        vim_networks = nsir_db.get_vim_networks_info(nsi_id)
        log_queue.put(["INFO", "In OSM Wrapper TERMINATE, vim networks is:"])
        log_queue.put(["INFO", dumps(vim_networks, indent=4)])
        delete_networks(vim_networks)
        log_queue.put(["INFO", "*****Time measure: OSMW deleted networks OSM"])

    def onboard_nsd(self, nsd_json):
        """
        Performs the translation of the IFA014 NSD json to OSM format.
        Parameters
        ----------
        nsd_json: dict
            IFA014 network service descriptor.
        Returns
        -------
        """
        # perform the translation from IFA014 to OSM: for every df and il
        list_osm_json, default_index = ifa014_conversion(nsd_json)
        log_queue.put(["INFO", "TRANSLATING NSD from IFA014 to OSM"])
        for osm_json in list_osm_json:
            # generate the tar.gz folder
            package, package_folder = create_osm_files(osm_json, upload_folder)
            # upload the package to osm
            try:
                self.client.package.upload(package)
                shutil.rmtree(package_folder)
                os.remove(package)
            except ClientException as inst:
                log_queue.put(["INFO", "{}".format(inst)])

    def onboard_vnfd(self, vnfd_json):
        """
        Performs the translation of the IFA011 VNFD json to OSM format.
        Parameters
        ----------
        vnfd_json: dict
            IFA011 virtual network function descriptor
        Returns
        -------
        To be defined
        """
        # perform the translation from IFA011 to OSM
        list_osm_json = [ifa011_conversion(vnfd_json)]
        log_queue.put(["INFO", "TRANSLATING NSD from IFA011 to OSM"])
        for osm_json in list_osm_json:
            # generate the tar.gz folder
            package, package_folder = create_osm_files(osm_json, upload_folder)
            # upload the package to osm
            try:
                self.client.package.upload(package)
                shutil.rmtree(package_folder)
                os.remove(package)
            except ClientException as inst:
                log_queue.put(["INFO", "{}".format(inst)])
