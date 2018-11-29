# Author: Jordi Baranda
# Copyright (C) 2018 CTTC/CERCA
# License: To be defined. Currently use is restricted to partners of the 5G-Transformer project,
#          http://5g-transformer.eu/, no use or redistribution of any kind outside the 5G-Transformer project is
#          allowed.
# Disclaimer: this software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.

"""
File description
"""
# python imports
from random import randint
from six.moves.configparser import RawConfigParser
from http.client import HTTPConnection
from json import dumps
import requests
import time

# project imports
from coreMano.osm_db import osm_db
from nbi import log_queue

# osm imports
from osmclient.client import Client as client
from osmclient.common.exceptions import ClientException
from osmclient.common.exceptions import NotFound


########################################################################################################################
# PRIVATE METHODS COMPUTE                                                                                              #
########################################################################################################################


def get_information_of_deployed_service_os(ns_name, placement_info):
    vim_info = get_vim_info()
    service_vnf_info = list()
    #self.logger.info("The placement_info is: %s", placement_info)
    vnfs = []
    openstack_info = {}
    # get the info of the involved vims
    for vim in placement_info:  # be careful, I am assuming there are not zones in this version. Different zones have the same "control IP"
        vim_ip = vim_info[vim["NFVIPoPID"]]['ip']
        vim_token = vim_info[vim["NFVIPoPID"]]['token']
        openstack_info[vim["NFVIPoPID"]] = make_request2('GET', vim_ip, 'http://' + vim_ip +
                                                         '/compute/v2.1/servers', None, vim_token)
        for vnf in vim["mappedVNFs"]:
            #self.logger.info("vnf con id: %s", vnf)
            vnf_name = vnf
            for vm in openstack_info[vim["NFVIPoPID"]]["servers"]:
                # condition for OSM R3, creates the machine in openstack as: ns_name.vnf_name.vnfindex.vnf_id
                # if ( (vm["name"].find(ns_name + '-' + str(vnf['member-vnf-index'])) !=
                # -1) or (vm["name"].find(ns_name + '.' + vnf_name) !=-1) ):
                if ((vm["name"].find(ns_name + '.' + vnf_name) != -1)):
                    port_info = []  # list with each one of the interfaces of the vm
                    elem_port_info = []
                    identifier = vm["id"]
                    #self.logger.info("el identifier de la maquina virtual es: %s", str(identifier))
                    resource_ip_mac = make_request2('GET', vim_ip, 'http://' + vim_ip +
                                                    '/compute/v2.1/servers/' + identifier + '/os-interface',
                                                    None, vim_token)
                    #self.logger.info("la informacion de RESOURCE_IP_MAC es: %s", resource_ip_mac)
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
                 # vnf_info = {"name": vnf_name, "vnfr": vnf['vnfr-id'], "dc": vnf['rw-nsr:datacenter'],
                 #             "port_info": port_info, "volumes": volumes}
                 # vnf_info = {"name": vnf_name, "vnfr": vnf['vnfr-id'], "dc": vnf['rw-nsr:datacenter'],
                 #             "port_info": port_info} #R3
                    vnf_info = {"name": vnf_name, "dc": vim["NFVIPoPID"], "port_info": port_info}  # R4
                    service_vnf_info.append(vnf_info)
    #self.logger.info("service vnf info: %s", service_vnf_info)
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
    #logger.debug('In method get_token with params ' + ip + ', ' + user + ', ' + password + ', ' + tenant)
    log_queue.put(["INFO", "In EECOMPUTE, get_token"])
    uri = 'http://' + ip + '/identity/v3/auth/tokens'
#    body = {'auth': {'identity': {'methods': ['password'],
#                                  'password': {'user': {'name': user,
#                                                        'domain': {"id": "default"},
#                                                        'password': password}
#                                               },
#                  'scope': {'project': { 'name': tenant,
#                                                         'domain': {"id": "default"}}
#                                           }
#                                  }
#                     }
#            }

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

    # TODO handle exceptions to make sure connection is properly closed
    # get the connection and make the request
    conn = HTTPConnection(ip, 80, timeout=10)
    conn.request('POST', uri, dumps(body), header)

    # read the response and close connection
    rsp = conn.getresponse()
    conn.close()
    rsp.read()  # needed to empty buffer even if not used

    # if result is not OK, raise Exception
    if rsp.status not in [200, 201]:
        #logger.warning('Error: ' + str(rsp.status) + ', ' + rsp.reason)
        raise HTTPException('Error: ' + str(rsp.status) + ', ' + rsp.reason)

    # get token from header
    rsp_header = rsp.getheaders()
    token = rsp_header[2][1]
    log_queue.put(["INFO", "In EECOMPUTE, rsp_header is:"])
    log_queue.put(["INFO", rsp_header])
    log_queue.put(["INFO", "In EECOMPUTE, Token is:"])
    log_queue.put(["INFO", token])
    return token


def get_vim_info():
    # self.vim_info
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
        vim_info[identifier]['token'] = get_token(vim_info[identifier]['ip'],
                                                  vim_info[identifier]['user'],
                                                  vim_info[identifier]['password'])
    return vim_info


########################################################################################################################
# PRIVATE METHODS NETWORK                                                                                              #
########################################################################################################################


def create_os_networks(info_to_create_networks):
    log_queue.put(["INFO", "In EECOMPUTE, create_os_networks"])
    # network_ids = []
    vim_info = get_vim_info()
    log_queue.put(["DEBUG", "vim_info"])
    log_queue.put(["DEBUG", dumps(vim_info, indent=4)])
    log_queue.put(["DEBUG", "info_to_create_networks"])
    log_queue.put(["DEBUG", dumps(info_to_create_networks, indent=4)])

    info_to_create_networks['network_ids'] = {}
    # vim_info está en OSM_Jordi/5GTRANSFORMER/SM/servicemanager_osnetworks_multivim_R3_R4_COREMANO.py
    for key in info_to_create_networks['name'].keys():
        number_of_vims = len(info_to_create_networks['name'][key])
        number_ips_in_pool = int(253 / number_of_vims)  # assuming it is /24
        vim_index = 0
        for vim in info_to_create_networks['name'][key]:
            network_ids = []
            vim_ip = vim_info[vim]['ip']
            vim_token = vim_info[vim]['token']
            # print info_to_create_networks['name'][i], info_to_create_networks['vlan_id'][i], info_to_create_networks['cidr'][i]
            # create the network
            body = {"network": {
                "admin_state_up": 'true',
                "name": key,
                "provider:network_type": "vlan",
                "provider:physical_network": "public",
                "provider:segmentation_id": info_to_create_networks['vlan_id'][key],
                "shared": "true",
                "router:external": "true"
            }
            }
            resources = make_request2('POST', vim_ip, 'http://' + vim_ip + ':9696/v2.0/networks', body, vim_token)
            log_queue.put(["DEBUG", dumps(resources, indent=4)])
            network = resources['network']['id']
            # network_ids.append(network)
            network_name = resources['network']['name']
            # create the subnet
            # be careful with dhcps, they consume ips and they can be in other vim's!!
            start_ip = 2 + number_ips_in_pool * vim_index
            end_ip = start_ip + number_ips_in_pool - 1
            body = {"subnet": {
                "network_id": network,
                "name": network_name + "-subnet",
                "ip_version": 4,
                "cidr": "192.168." + str(info_to_create_networks['cidr'][key]) + ".0/24",
                "allocation_pools": [{"start": "192.168." + str(info_to_create_networks['cidr'][key]) + '.' + str(start_ip),
                                      "end":   "192.168." + str(info_to_create_networks['cidr'][key]) + '.' + str(end_ip)}],
                "gateway_ip": "192.168." + str(info_to_create_networks['cidr'][key]) + ".1",
                "enable_dhcp": 'true'
            }
            }
            # make_request en openstack_interface.py
            resources = make_request2('POST', vim_ip, 'http://' + vim_ip + ':9696/v2.0/subnets', body, vim_token)
            # by default adds a dhcp agent to the network when addint the subnet
            # associate the dhcp agent for this network
            dhcp_agents = get_dhcp_agents(vim_info)
            for agent in dhcp_agents[vim]:
                body = {"network_id": network}
                for da in agent.keys():
                    resources = make_request2('POST', vim_ip, 'http://' +
                                              vim_ip + ':9696/v2.0/agents/' +
                                              agent[da] + '/dhcp-networks', body, vim_token)
            if not vim_info[vim]['vimId'] in info_to_create_networks['network_ids']:
                info_to_create_networks['network_ids'][vim_info[vim]['vimId']] = []
            info_to_create_networks['network_ids'][vim_info[vim]['vimId']].append(network)
            vim_index = vim_index + 1
    return info_to_create_networks


def delete_networks(info_to_create_networks):
    vim_info = get_vim_info()
    for key in info_to_create_networks['cidr'].keys():
        vlan_id = int(info_to_create_networks['vlan_id'][key])
        # log_queue.put(["INFO", "the vlan_id is: %s" % vlan_id ])
        cidr = int(info_to_create_networks['cidr'][key])
        # log_queue.put(["INFO", "the cidr is: %s" % cidr ])
        osm_db.remove_used_vlan(int(vlan_id))
        osm_db.remove_used_cidr(int(cidr))
    for key in info_to_create_networks['network_ids'].keys():
        vim_ip = vim_info[key]['ip']
        vim_token = vim_info[key]['token']
        # for network in info_to_create_networks['network_ids'][key]:
        for network in info_to_create_networks['network_ids'][key]:
            log_queue.put(["DEBUG", dumps(network, indent=4)])
            # ports = make_request2('GET', vim_ip, 'http://' + vim_ip + ':9696/v2.0/ports?network_id='+ network, None, vim_token)
            # for port in ports["ports"]:
            #    if (port['device_owner'] == "network:dhcp"):
            #        body = json.dumps({'mac': port['mac_address']})
            #        res = requests.delete(self.RYU_uri_base + 'v1.0/topology/hosts', data=body)
            # delete the network
            make_request2('DELETE', vim_ip, 'http://' + vim_ip + ':9696/v2.0/networks/' + network, None, vim_token)


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
    # ask mtp to deploy vl
    pass


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
    pass


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


def deploy_vls_vim(nsId, nsd_json, instantiationLevel, resources, placement_info):
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
    #descriptor = self.MANOclient.client.nsd.get(nsd_name)
    # { "vl_id": [NFVIPoP1, NFVIPoP2...], ...} variable which includes the involved vim's in the different vld of the nsd
    log_queue.put(["INFO", "In EECOMPUTE, deploy vls vim"])
    virtual_link_vim = {}
    ll_pops = {}
    for vl in nsd_json["nsd"]["virtualLinkDesc"]:
        virtual_link_vim[vl["virtualLinkDescId"]] = []
    for LL in resources["LLs"]:
        ll_pops[LL["LLid"]] = [LL["source"]["Id"], LL["destination"]["Id"]]

    for vl in placement_info["usedVLs"]:
        for mvl in vl["mappedVLs"]:
            if not vl["NFVIPoP"] in virtual_link_vim[mvl]:
                virtual_link_vim[mvl].append(vl["NFVIPoP"])
    for ll in placement_info["usedLLs"]:
        for mvl in ll["mappedVLs"]:
            log_queue.put(["DEBUG", virtual_link_vim[mvl]])
            log_queue.put(["DEBUG", ll_pops[ll["LLID"]][0]])

            if not ll_pops[ll["LLID"]][0] in virtual_link_vim[mvl]:
                virtual_link_vim[mvl].append(ll_pops[ll["LLID"]][0])
            if not ll_pops[ll["LLID"]][1] in virtual_link_vim[mvl]:
                virtual_link_vim[mvl].append(ll_pops[ll["LLID"]][1])

    # cidr_id y vlan_id is global for all the network services
    info_to_create_networks = {'ns_name': nsId,
                               'nsd_name': nsd_json["nsd"]["nsdIdentifier"], 'name': {}, 'vlan_id': {}, 'cidr': {}}
    used_vim_vlans = osm_db.get_used_vlans()
    used_vim_cidrs = osm_db.get_used_cidrs()
    for network in virtual_link_vim.keys():
        if len(virtual_link_vim[network]) > 0:
            # loop to create the vlan_id
            while True:
                vlan_id = randint(1, 4094)
                # if vlan_id not in info_to_create_networks['vlan_id']:
                if used_vim_vlans is None or vlan_id not in used_vim_vlans:
                    break
            # loop to create the CIDR value
            while True:
                cidr_id = randint(0, 256)
                # if cidr_id not in info_to_create_networks['cidr']:
                if used_vim_cidrs is None or cidr_id not in used_vim_cidrs:
                    break
            network_id = network + '_custom_' + nsId + '_' + str(vlan_id)
            info_to_create_networks['name'][network_id] = virtual_link_vim[network]
            info_to_create_networks['vlan_id'][network_id] = str(vlan_id)
            osm_db.add_used_vlan(vlan_id)
            vlans = osm_db.get_used_vlans()
            log_queue.put(["DEBUG", "OSM VLANS:"])
            log_queue.put(["DEBUG", vlans])
            info_to_create_networks['cidr'][network_id] = str(cidr_id)
            osm_db.add_used_cidr(cidr_id)
    # print "ns_name: ", ns_name[i], "created_networks: ", info_to_create_networks
    info_to_create_networks = create_os_networks(info_to_create_networks)
    # print info_to_create_networks
    # network_vim_management[nsId] = info_to_create_networks  # pasar a db de instancias
    return info_to_create_networks


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
#     for vl in vl_list:
#         uninstall(vl)


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

    # Create NS according to version osm ns-create2
    def create_ns(self, ns_name, nsd_name, distribution, config, ssh_keys=None):

        # logger.info("ns_name: %s, nsd_name: %s, distribution: %s, configuration: %s",
        #            ns_name, nsd_name, distribution, config)

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

    # Get information of the instantiation process at OSM
    def get_information_of_deployed_service(self, ns_name, number_vnfs):
        log_queue.put(["INFO", "In OSM Wrapper, get information deployed service"])
        timeout = number_vnfs * 60  # we give 60*n seconds to launch n VM's with openstack
        start_time = time.time()
        current_time = 0
        nsr = None
        while ((current_time < timeout) and nsr == None):
            # #logger.info("Entro en bucle")
            nsr = self.get_service_status(ns_name)
            if nsr is not None:
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
            # #logger.info("evaluando servicio: %s", nsopdata)
            if (nsr['name-ref'] == ns_name):
                # #logger.info("He encontrado el servicio: %s", ns_name)
                if ((nsr['operational-status'] == 'running') and (nsr['config-status'] == 'configured')):
                    return resp['nsd']
                else:
                    return None
        else:
            if ((resp['operational-status'] == 'running') and (resp['config-status'] == 'configured')):
                # #logger.info("resssssppp: %s", resp)
                return resp['nsd']
            else:
                return None


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
        # TODO use properties
        log_queue.put(["INFO", "In OSM Wrapper"])
        self.host_ip = host_ip
        self.ro_host = ro_ip
        self.release = release
        if self.release == "3":
            self.client = client(host=self.host_ip, ro_host=self.ro_host)  # init the client
        else:
            self.client = client(host=self.host_ip, sol005=True)

    def instantiate_ns(self, nsi_id, ns_descriptor, body, placement_info, resources):
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
        config = deploy_vls_vim(nsi_id, ns_descriptor, instantiationLevel, resources, placement_info)
        # pass nsi_id as ns_name
        # in osm dbs, nsds will stored under the following convention: "nsdIdentifier_instantiationlevel"
        log_queue.put(["INFO", "In OSM Wrapper, instantiate_ns"])
        distrib = self.adapt_placement_to_osm(
            placement_info['usedNFVIPops'], ns_descriptor["nsd"]['nsdIdentifier'] + '_' + body.flavour_id + '_' + body.ns_instantiation_level_id)
        r = self.create_ns(nsi_id, ns_descriptor['nsd']['nsdIdentifier'] + '_' + body.flavour_id + '_' +
                           body.ns_instantiation_level_id, config=config, distribution=distrib)
        if r is not None:
            number_vnfs = len(placement_info)
            #nsr = self.get_information_of_deployed_service(nsi_id, number_vnfs)
            nsr = get_information_of_deployed_service_os(nsi_id, placement_info["usedNFVIPops"])
            log_queue.put(["INFO", "In OSM Wrapper, instantiate_ns return is:"])
            log_queue.put(["INFO", dumps(nsr, indent=4)])
            return nsr
        else:
            return None

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
        #logger.info("Deleting ns_name: %s", nsi_id)
        try:
            self.client.ns.delete(nsi_id)
            return "OK"
        except ClientException as inst:
            log_queue.put(["INFO", "%s" % inst.message])
            return None

            # remove the created networks at the different vims
#        vim_networks = nsir_db.get_vim_networks_info(nsId)
#        delete_networks(vim_networks)
