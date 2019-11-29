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

import copy
import json
import os
from collections import OrderedDict
from configparser import RawConfigParser
from coreMano.cloudify_wrapper_lib.converter_nsd_openstack_yaml import Falvor
from db.ns_db import ns_db
from db.nsir_db import nsir_db


# load static properties
static_parameters_propertires = RawConfigParser()
static_parameters_propertires.read("../../coreMano/staticParameters.properties")

# load coreMano properties
config_core_mano = RawConfigParser()
config_core_mano.read("../../coreMano/coreMano.properties")
pa_pa_enable = config_core_mano.get("PA", "pa_enable")
pa_pa_simulate = config_core_mano.get("PA", "pa_simulate")
# load mtp properties
config_mtp = RawConfigParser()
config_mtp.read("../../mtp.properties")
mtp_ip = config_mtp.get("MTP", "mtp.ip")
mtp_port = config_mtp.get("MTP", "mtp.port")
mtp_path = config_mtp.get("MTP", "mtp.base_path")


class ConverterNSDMTPYAML(object):
    def __init__(self):
        self.networks = {}
        self.servers = {}
        self.ns_descriptor = {}
        self.__vnfds_descriptor = {}
        self.__ns_instantiation_level_id = ""
        self.__ns_service_id = ""
        self.cloudify_blueprint = CloudifyBlueprint()
        self.__nfvis_pop_info = {}
        self.__map_network_sap = {}
        self.__output_object = {}
        self.__placement_info = {}
        self.__static_parameters = None
        self.__nested_info = None
        self.__start_vlan = ""
        self.__default_key_name = ""
        self.__install_cloudify_agent = "no"
        self.__additional_param_for_ns = None

    def set_additional_param_for_ns(self, additional_param_for_ns):
        self.__additional_param_for_ns = additional_param_for_ns

    def set_start_vlan(self, start_vlan):
        self.__start_vlan = start_vlan

    def default_key_name(self, default_key_name):
        self.__default_key_name = default_key_name

    def install_cloudify_agent(self, install_cloudify_agent):
        self.__install_cloudify_agent = install_cloudify_agent

    def set_ns_instantiation_level_id(self, ns_instantiation_level_id):
        self.__ns_instantiation_level_id = ns_instantiation_level_id

    def set_ns_service_id(self, ns_service_id):
        self.__ns_service_id = ns_service_id

    def set_vnfds_descriptor(self, vnfds_descriptor):
        self.__vnfds_descriptor = vnfds_descriptor

    def set_ns_descriptor(self, ns_descriptor):
        self.ns_descriptor = ns_descriptor
        nsd_identifier = self.ns_descriptor['nsd']['nsdIdentifier']
        static_parameters = static_parameters_propertires.get("STATIC_PARAMETERS", nsd_identifier, fallback=None)
        if static_parameters is not None:
            self.__static_parameters = json.loads(static_parameters)
        else:
            self.__static_parameters = None

    def get_ns_descriptor(self):
        return self.ns_descriptor

    def set_servers(self, servers):
        self.servers = servers

    def get_servers(self):
        return self.servers

    def set_networks(self, networks):
        self.networks = networks

    def get_networks(self):
        return self.networks

    def sort_servers(self):
        key_servers = sorted(self.servers, reverse=False)
        servers = {}
        for key_server in key_servers:
            servers[key_server] = self.servers[key_server]

        self.servers = servers

    def sort_networks(self):
        key_networks = sorted(self.networks, reverse=False)
        networks = {}
        for key_network in key_networks:
            networks[key_network] = self.networks[key_network]
        self.networks = networks

    def get_vnfd(self, vnfdid):
        return self.__vnfds_descriptor[vnfdid]

    def getnetwork(self, virtual_link_profile_id):
        virtual_link_profiles = self.ns_descriptor['nsd']['nsDf'][0]['virtualLinkProfile']
        for virtual_link_profile in virtual_link_profiles:
            if virtual_link_profile['virtualLinkProfileId'] == virtual_link_profile_id:
                return virtual_link_profile['virtualLinkDescId']

    def getserver(self, vnf_profile_id):
        vnf_profiles = self.ns_descriptor['nsd']['nsDf'][0]['vnfProfile']
        vnfp = {}
        for vnf_profile in vnf_profiles:
            if vnf_profile['vnfProfileId'] == vnf_profile_id:
                vnfp = vnf_profile
                break

        # server name
        vnfd_id = vnfp['vnfdId']
        server = {vnfd_id: {"relations": {}}}
        if 'script' in vnfp.keys():
            server[vnfd_id]['script'] = copy.deepcopy(vnfp['script'])
        server[vnfd_id]['relations']['ports'] = {}
        server[vnfd_id]['vnfProfileId'] = vnf_profile_id
        ns_virtual_links = vnfp['nsVirtualLinkConnectivity']
        for ns_virtual_link in ns_virtual_links:
            ports = ns_virtual_link['cpdId']
            virtual_link_profile_id = ns_virtual_link['virtualLinkProfileId']
            network_name = self. getnetwork(virtual_link_profile_id)
            self.networks.update({network_name: {}})
            for port in ports:
                server[vnfd_id]['relations']['ports'].update({port: {'network': network_name}})
        return server

    def set_nfvis_pop_info(self, nfvis_pop_info):
        self.__nfvis_pop_info = nfvis_pop_info

    def set_placement_info(self, placement_info):
        self.__placement_info = copy.deepcopy(placement_info)

    #   change script args depend on number instances
    def change_script_args(self, script, server_name, new_server_name, port_name, new_port_name):
        for arg, arg_value in script['args'].items():
            arg_parts = arg_value.split(".")
            if len(arg_parts) > 5:
                if arg_parts[1] == server_name and arg_parts[5] == port_name:
                    arg_parts[1] = new_server_name
                    arg_parts[5] = new_port_name
                    return_arg = ".".join(arg_parts)
                    script['args'][arg] = return_arg

    def set_nested_info(self, nested_info):
        self.__nested_info = nested_info

    def parse(self):
        # Create map network sapd
        sapds = self.ns_descriptor['nsd']['sapd']
        for sapd in sapds:
            self.__map_network_sap.update({sapd['nsVirtualLinkDescId']: sapd['cpdId']})

        # get description for nsInstantiationLevel
        ns_i_ls = self.ns_descriptor['nsd']['nsDf'][0]['nsInstantiationLevel']
        ns_instantiation_level = {}
        for ns_il in ns_i_ls:
            if self.__ns_instantiation_level_id == ns_il['nsLevelId']:
                ns_instantiation_level = ns_il
        vnf_to_level_mapping = ns_instantiation_level['vnfToLevelMapping']

#       Servers
        for vnf in vnf_to_level_mapping:
            vnf_profile_id = vnf['vnfProfileId']
            server = self.getserver(vnf_profile_id)
            self.servers.update(server)

#       parse flvavor, sw, ports
        nsd_identifier = self.ns_descriptor['nsd']['nsdIdentifier']
        for server_name in self.servers.keys():
            vnfd = self.get_vnfd(server_name)
            vcpus = vnfd['virtualComputeDesc'][0]['virtualCpu']['numVirtualCpu']
            ram = vnfd['virtualComputeDesc'][0]['virtualMemory']['virtualMemSize']
            disk = vnfd['virtualStorageDesc'][0]['sizeOfStorage']
            sw_image = vnfd['vdu'][0]['swImageDesc']['swImage']
            user_image = vnfd['vdu'][0]['swImageDesc']['user_image']
            flavor = {
                'flavor_name': "flavor_" + server_name,
                'vcpus': vcpus,
                'ram': ram,
                'disk': disk
            }
            self.servers[server_name].update({'flavor': flavor})
            self.servers[server_name].update({'swImage': sw_image})
            self.servers[server_name].update({'userImage': user_image})
            self.servers[server_name].update({'NFVIPoPID': "1"})
            ports = self.servers[server_name]['relations']['ports']

            for port_name, port_object in ports.items():
                vnfd_ports = vnfd['vnfExtCpd']
                for vnfs_port in vnfd_ports:
                    if vnfs_port['cpdId'] == port_name:
                        floating_ip_activated = vnfs_port['addressData'][0]['floatingIpActivated']
                        self.servers[server_name]['relations']['ports'][port_name].\
                            update({'floatingIp': floating_ip_activated})
                        network_name = port_object['network']
                        self.networks[network_name].update({'name': network_name})
                        self.networks[network_name].update({'nsid_name': self.__ns_service_id + "_" + network_name})
                        if "number_ports" in self.networks[network_name]:
                            self.networks[network_name]['number_ports'] += 1
                        else:
                            self.networks[network_name].update({'number_ports': 10})
#                       skip if network contain pool
                        if "pool_start" in self.networks[network_name]:
                            continue
                        self.networks[network_name].update({'connect_to_Router': floating_ip_activated})
                        self.networks[network_name].update({"provider": False})
                        self.networks[network_name].update({'NFVIPoPID': "1"})
                        break

        third_octet = 1
        for network_name, network_value in self.networks.items():
            self.networks[network_name].update({'ip_network': "192.168." + str(third_octet) + ".0/24"})
            third_octet += 1

        # set static network cidr from properties
        if self.__static_parameters:
            for key, value in self.__static_parameters.items():
                key_split = key.split(".")
                # set static network cidr
                if key_split[0:2] == ["inf", "vl"] and key_split[3] == "cidr":
                    if key_split[2] in self.networks.keys():
                        self.networks[key_split[2]].update({"ip_network": value})

                if key_split[0] == "vnf" and key_split[2] == "vdu" and key_split[4] == "extcp":
                    #check if exists server with name key_split[1]
                    if key_split[1] in self.servers.keys():
                        # check if exists interface name key_split[5]
                        if key_split[5] in self.servers[key_split[1]]['relations']['ports'].keys():
                            # set static ip and mac address
                            if key_split[6] == "address":
                                self.servers[key_split[1]]['relations']['ports'][key_split[5]].update(
                                {key_split[7]: value})
                            # set static floating ip
                            if key_split[6] == "floating":
                                self.servers[key_split[1]]['relations']['ports'][key_split[5]].update(
                                {"floating_ip_address": value})

        #set address pool
        if self.__nested_info is None:
            pool_number = 0
        else:
            nested_service_info = ns_db.get_nested_service_info(self.__ns_service_id)
            if nested_service_info is None:
                pool_number = 0
            else:
                pool_number = len(nested_service_info) - 1

        if pool_number < 0:
            pool_number = 0

        for network_name, network_value in self.networks.items():
            network_value.update({"address_pool": [pool_number]})

        # network and vlan for already installed deployment
        # if nested_service_info is not None:
        #     for nested_service in nested_service_info:
        #         nested_instance_id = nested_service['nested_instance_id']
        #         try:
        #             vim_networks_info = nsir_db.get_vim_networks_info(nested_instance_id)
        #             for network_name, network_value in self.networks.items():
        #                 full_network_name = self.__ns_service_id + "_" + network_name
        #                 if full_network_name in vim_networks_info['cidr'].keys():
        #                     network_value['ip_network'] = vim_networks_info['cidr'][full_network_name]
        #                     network_value['vlan'] = vim_networks_info['vlan'][full_network_name]
        #         #               if vim_networks_info wasn't found for nested_instance_id
        #         except KeyError:
        #             pass

        if self.__start_vlan is not None and self.__start_vlan != "":
            vlan = int(self.__start_vlan)
            for network_name, network_value in self.networks.items():
                network_value.update({"vlan" : vlan})
                vlan = vlan + 1
        else:
            for network_name, network_value in self.networks.items():
                network_value.update({"vlan": ""})

        #PA
        # added NFVIPoPID to servers
        if pa_pa_enable == "true" or pa_pa_simulate == "true":
            for server_name in self.servers.keys():
                for used_nfvi_pops in self.__placement_info['usedNFVIPops']:
                    if server_name in used_nfvi_pops['mappedVNFs']:
                        self.servers[server_name].update({'NFVIPoPID': used_nfvi_pops['NFVIPoPID']})

        # added NFVIPoPID to networks VL
        if pa_pa_enable == "true" or pa_pa_simulate == "true":
            for network in self.networks:
                for used_vl in self.__placement_info['usedVLs']:
                    if network in used_vl['mappedVLs']:
                        self.networks[network].update({'NFVIPoPID': used_vl['NFVIPoP']})

        # if nested_service_info is None:
        # # flow without federation

        # PA add interpop network
        new_netwoks = {}

        for server_name, sever_value in self.servers.items():
            server_nfvi_po_pid = sever_value['NFVIPoPID']
            for port_name, port_value in sever_value['relations']['ports'].items():
                for used_ll in self.__placement_info['usedLLs']:
                    if port_value['network'] in used_ll['mappedVLs']:
                        new_network_name = port_value['network'] + "_" + server_nfvi_po_pid
                        new_netwoks[new_network_name] = copy.deepcopy(self.networks[port_value['network']])
                        new_netwoks[new_network_name].update({"provider": True})
                        new_netwoks[new_network_name].update({'NFVIPoPID': server_nfvi_po_pid})
                        port_value['network'] = new_network_name
        self.networks.update(new_netwoks)

        # PA delete old interpop network
        for used_ll in self.__placement_info['usedLLs']:
            for mappedVL in used_ll['mappedVLs']:
                if mappedVL in self.networks.keys():
                    del self.networks[mappedVL]

        #federation
        if self.__nested_info:

            #change network name in networks
            new_netwoks = {}
            for network_name in self.networks.keys():
                new_network_name = None
                for network_name_from_nested_info in self.__nested_info[nsd_identifier][0]:
                    if network_name in network_name_from_nested_info.keys():
                        new_nsid_network_name = network_name_from_nested_info[network_name]
                        new_network_name = new_nsid_network_name.replace(self.__ns_service_id + "_", "")
                if new_network_name is not None:
                    new_netwoks[new_network_name] = copy.deepcopy(self.networks[network_name])
                    new_netwoks[new_network_name]['name'] = new_network_name
                    new_netwoks[new_network_name]['nsid_name'] = new_nsid_network_name
                    new_netwoks[new_network_name]['provider'] = True
                    new_netwoks[new_network_name]['ip_network'] =  \
                        self.__nested_info[nsd_identifier][1]['networkInfo']['cidr'][network_name]
                    free_pools = list(range(0,13))
                    for i in self.__nested_info[nsd_identifier][1]['networkInfo']['addressPool'][network_name]:
                        free_pools.remove(i)
                    new_netwoks[new_network_name]['address_pool'] = [free_pools[0]]

                else:
                    new_netwoks[network_name] = copy.deepcopy(self.networks[network_name])
            self.networks = new_netwoks

            # change network name in servers
            for server_name, sever_value in self.servers.items():
                for port_name, port_value in sever_value['relations']['ports'].items():
                    network_name = port_value['network']
                    for network_name_from_nested_info in self.__nested_info[nsd_identifier][0]:
                        if network_name in network_name_from_nested_info.keys():
                            new_network_name = network_name_from_nested_info[network_name]
                            port_value['network'] = new_network_name
                            break

            # change network name in map_network_sap
            for map_network_sap_key, map_network_sap_value in self.__map_network_sap.items():
                for network_name_from_nested_info in self.__nested_info[nsd_identifier][0]:
                    if map_network_sap_key in network_name_from_nested_info.keys():
                        new_network_name = network_name_from_nested_info[map_network_sap_key]
                        self.__map_network_sap.update({new_network_name: map_network_sap_value})
                        del self.__map_network_sap[map_network_sap_key]

            # change change network name in placement_info usedVLs
            for network_name_from_nested_info in self.__nested_info[nsd_identifier][0]:
                for key_nested_info, value_nested_info in network_name_from_nested_info.items():
                    for key_placement_info, value_placement_info in enumerate(self.__placement_info['usedVLs']):
                        for key_mappedVLs, value_mappedVLs in enumerate(value_placement_info['mappedVLs']):
                            if key_nested_info == value_mappedVLs:
                                value_placement_info['mappedVLs'][key_mappedVLs] = value_nested_info

            # change change network name in placement_info usedLLs
            for network_name_from_nested_info in self.__nested_info[nsd_identifier][0]:
                for key_nested_info, value_nested_info in network_name_from_nested_info.items():
                    for key_placement_info, value_placement_info in enumerate(self.__placement_info['usedLLs']):
                        for key_mappedVLs, value_mappedVLs in enumerate(value_placement_info['mappedVLs']):
                            if key_nested_info == value_mappedVLs:
                                value_placement_info['mappedVLs'][key_mappedVLs] = value_nested_info

        # #add service_id to network name
        # for network_name, network_value in self.networks.items():
        #     if self.__ns_service_id not in network_value['name']:
        #         network_value['name'] = self.__ns_service_id + "_" + network_value['name']

        # for server_name in self.servers:
        #     print("server")

        # # set gateway
        object_dict_network_number = {}
        for network_name, network_value in self.networks.items():
            local_network_name = network_name.rsplit('_', 1)[0]
            pool_start = network_value['ip_network']
            octets = pool_start.split('.')
            forth_octet = octets[3].split('/')[0]
            if local_network_name in object_dict_network_number.keys():
                object_dict_network_number[local_network_name] += 1
            else:
                object_dict_network_number.update({local_network_name: 1})

            if len(network_value['address_pool']) == 0:
                network_value['address_pool'] = [0]
            else:
                network_value['address_pool'] = sorted(network_value['address_pool'])
            address_pool = network_value['address_pool'][0]
            if address_pool > 11:
                address_pool = 0
            forth_octet_gateway = int(forth_octet) + (address_pool * 20 + 1)
            octets[3] = str(forth_octet_gateway)
            network_value['gateway_ip'] = ".".join(octets)

#       add instances depent on numberOfInstances
        new_servers = {}
        for server_name in self.servers:
            number_of_instances = 1
            for vnfd_profile in vnf_to_level_mapping:
                if self.servers[server_name]['vnfProfileId'] == vnfd_profile['vnfProfileId']:
                    number_of_instances = vnfd_profile['numberOfInstances']
                    break

            if number_of_instances > 1:
                instance_number = 2
                while instance_number <= number_of_instances:
                    new_server_name = server_name + "_" + str(instance_number).zfill(2)
                    new_servers.update({new_server_name: copy.deepcopy(self.servers[server_name])})
                    new_ports = {}
                    for port_name, port_value in new_servers[new_server_name]['relations']['ports'].items():
                        new_port_name = port_name + "_" + str(instance_number).zfill(2)
                        # change name in scripts
                        if "script" in new_servers[new_server_name]:
                            for script in new_servers[new_server_name]['script']:
                                for script_name, script_value in script.items():
                                    if script_name == "target":
                                        if script_value == server_name:
                                            script['target'] = new_server_name
                                        continue
                                    self.change_script_args(script_value,
                                                            server_name, new_server_name,
                                                            port_name, new_port_name)
                        new_ports[new_port_name] = port_value
                    new_servers[new_server_name]['relations']['ports'] = new_ports
                    instance_number += 1
        self.servers.update(new_servers)

#       convert script agruments to cloudify format
        for server_name, server_value in self.servers.items():
            if "script" in server_value:
                for script in server_value['script']:
                    for script_name, script_value in script.items():
                        if script_name == "target":
                            continue
                        for arg_name, arg_value in script_value['args'].items():
                            arg_parts = arg_value.split(".")
                            for server_name_2, server_value_2 in self.servers.items():
#                                   find network by port
                                for port_name, port_value in server_value_2['relations']['ports'].items():
                                    if arg_parts[0] == "vnf" and arg_parts[6] == "address":
                                        if arg_parts[5] == port_name:
                                            network_object_name = port_value['network']
                                            network_name = self.networks[network_object_name]['name']
                                            arg_return = "{ get_attribute: [" + arg_parts[1] + ", external_resource, " + \
                                                         "virtualNetworkInterface, " + \
                                                         network_name + ", ipAddress, 0] }"
                                            script_value['args'][arg_name] = arg_return
                                    if arg_parts[0] == "vnf" and arg_parts[6] == "floating":
                                        if arg_parts[5] == port_name:
                                            network_object_name = port_value['network']
                                            network_name = self.networks[network_object_name]['name']
                                            arg_return = "{ get_attribute: [" + arg_parts[1] + ", external_resource, " + \
                                                         "virtualNetworkInterface, " + \
                                                         network_name + ", floatingIP] }"
                                            script_value['args'][arg_name] = arg_return

    def generate_yaml(self, file_name):
        script_name = "script_"

        self.cloudify_blueprint.add_start_comment("# \n # \n")
        self.cloudify_blueprint.add_tosca_version("cloudify_dsl_1_3")
        import_sources = ['http://www.getcloudify.org/spec/cloudify/4.3/types.yaml', 'plugin:cloudify_mtp_plugin']
        self.cloudify_blueprint.add_import(import_sources)

        dsl_definiftion = OrderedDict()
        mtp_config = {
            'url': 'http://' + mtp_ip + ':' + mtp_port
        }

        mtp_config = OrderedDict(mtp_config)
        dsl_definiftion['mtp_config'] = mtp_config
        self.cloudify_blueprint.add_dsl_definiftions(dsl_definiftion)

        for server_name, server in self.servers.items():
            #flavor yaml creation
            flavor_yaml = Falvor()
            flavor_yaml.set_openstack_config('nfvi_pop_' + server['NFVIPoPID'])
            flavor_yaml.set_vcpus(server['flavor']['vcpus'])
            flavor_yaml.set_ram(server['flavor']['ram'])
            flavor_yaml.set_disk(server['flavor']['disk'])
            flavor_yaml.set_name("flavor_" + server_name)
            #server yaml creation
            server_yaml = Server()
            server_yaml.set_name(server_name)
            server_yaml.set_install_cloudify_agent(self.__install_cloudify_agent)
            server_yaml.set_flavor_name(server['flavor']['flavor_name'])
            server_yaml.set_image(server['swImage'])
            server_yaml.set_key_name(self.__default_key_name)
            server_yaml.set_user_image(server['userImage'])
            server_yaml.set_nfvi_pop_id(server['NFVIPoPID'])
            server_yaml.set_ns_service_id(self.__ns_service_id)
            for port_name, port in server['relations']['ports'].items():
                server_yaml.add_network(port)
                if port['floatingIp'] != True:
                    continue
                network = self.networks[port['network']]
                sapd = self.__map_network_sap[network['name']]
#                   generate output object
                if sapd not in self.__output_object:
                    self.__output_object[sapd] = {}
                self.__output_object[sapd].update(
                    {server_name: "{get_attribute: [" + server_name + ", external_resource, " + \
                                  "virtualNetworkInterface, " + network['name'] +", floatingIP]}"})
            self.cloudify_blueprint.add_node_template(server_yaml.get_yaml())
            # self.cloudify_blueprint.add_node_template(flavor_yaml.get_yaml())
            if self.__install_cloudify_agent == "yes":
                #script yaml creation
                if "script" in server.keys():
                    for script in server['script']:
                        script_yaml = Script()
                        script_yaml.set_name(script_name + script['target'] + "_" + server_name)
                        script_yaml.set_contain_in(script['target'])
                        script_yaml.set_depend_on(server_name)
                        script_yaml.set_file_name_blueprint(file_name)
                        if "start" in script.keys():
                            script_yaml.start_script(script['start'])
                        if "start" in script.keys():
                            script_yaml.stop_script(script['stop'])
                        self.cloudify_blueprint.add_node_template(script_yaml.get_yaml())
        self.cloudify_blueprint.add_outputs(self.__output_object)

        # network yaml creation
        depend_on_network = ''
        for network_name, network in self.networks.items():
            private_network = PrivateNetwork()
            private_network.set_ns_service_id(self.__ns_service_id)
            private_network.set_object_name(network_name)
            private_network.set_name(network['nsid_name'])

            private_network.set_address_pool(network['address_pool'])
            private_network.set_network(network['ip_network'])
            private_network.set_nfvi_pop_id(network['NFVIPoPID'])
            if network['provider'] is True:
                private_network.set_type("subnet-vlan")
                private_network.set_interpop_vlan(network['vlan'])
            else:
                private_network.set_type("subnet")
            if network['connect_to_Router'] is True:
                private_network.connect_to_router()
                private_network.set_gateway_ip(network['gateway_ip'])
            if depend_on_network != '':
                private_network.depend_on("net_" + depend_on_network)
            depend_on_network = network_name
            self.cloudify_blueprint.add_node_template(private_network.get_yaml())
        data = self.cloudify_blueprint.get_blueprint()
        file = open(file_name, 'w')
        file.write(data)
        file.close()




class CloudifyBlueprint(object):
    def __init__(self):
        self.__start_comment = ""
        self.__imports = ""
        self.__dsl_definiftions = ""
        self.__inputs = ""
        self.__node_templates = ""
        self.__outputs = ""
        self.__tosca_version = ""

    def get_blueprint(self):
        return self.__start_comment + \
               self.__tosca_version + \
               self.__imports + \
               self.__dsl_definiftions + \
               self.__inputs + \
               self.__node_templates + \
               self.__outputs

    def add_start_comment(self, param):
        self.__start_comment = param

    def add_tosca_version(self, version):
        self.__tosca_version = "tosca_definitions_version: " + version + "\n\n"

    def add_import(self, import_sources):
        self.__imports = "imports:\n"
        for import_source in import_sources:
            self.__imports = self.__imports + "- " + import_source + "\n"
        self.__imports = self.__imports + "\n"

    def add_dsl_definiftions(self, dsl_definiftions):
        if len(self.__dsl_definiftions) == 0:
            self.__dsl_definiftions += "dsl_definitions:\n"

        for key1, value1 in dsl_definiftions.items():
            self.__dsl_definiftions += \
                                    "  " + key1 + ": &" + key1 + "\n"
            for key2, value2 in value1.items():
                self.__dsl_definiftions += \
                  "    " + key2 + ": " + value2 + "\n"
        self.__dsl_definiftions += "\n"

    def add_inputs(self, name, input_type, default):
        if len(self.__inputs) == 0:
            self.__inputs += "inputs:\n"
        self.__inputs += \
            "  " + name + ": \n" + \
            "    type: " + input_type + "\n" +  \
            "    default: " + default + "\n\n"

    def add_node_template(self, node_template):
        if len(self.__node_templates) == 0:
            self.__node_templates += "node_templates:\n\n"
        self.__node_templates += \
            node_template

    def add_outputs(self, output_object):
            self.__outputs += "" \
            "outputs:\n"

            for level1_key, level1_value in output_object.items():
                self.__outputs += "  " + level1_key + ":\n"
                self.__outputs += "    value:\n"
                for level2_key, level2_value in level1_value.items():
                    self.__outputs += "      " + level2_key + ": " + level2_value + "\n"


class Server(object):
    def __init__(self):
        self.__name = ""
        self.__flavor_name = ""
        self.__image = ""
        self.__relationships = ""
        self.__network_addresses = ""
        self.__openstack_config = ""
        self.__user_image = ""
        self.__nfvi_pop_id = ""
        self.__ns_server_id = ""
        self.__key_name = ""
        self.__install_cloudify_agent = ""

    def set_install_cloudify_agent(self, install_cloudify_agent):
        self.__install_cloudify_agent = install_cloudify_agent

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config

    def set_nfvi_pop_id(self, nfvi_pop_id):
        self.__nfvi_pop_id = nfvi_pop_id

    def get_yaml(self):

        if self.__install_cloudify_agent == "yes":
            cloudify_agent = \
            "         install_method: init_script\n"
        else:
            cloudify_agent = \
            "         install_method: none\n"

        yaml = "  " + self.__name + ":\n" \
            "    type: cloudify.mtp.compute\n" \
            "    properties:\n" \
            "      mtp_config: *mtp_config\n" \
            "      agent_config:\n" \
            + cloudify_agent +  \
            "         user: " + self.__user_image + "\n" \
            "      mtp_compute:\n" \
            "        affinityOrAntiAffinityConstraints:\n" \
            "        - affinityAntiAffinityResourceGroup: \"\"\n" \
            "          affinityAntiAffinityResourceList:\n" \
            "            resource:\n" \
            "            - \"\"\n" \
            "          scope: \"\"\n" \
            "          type: \"\"\n" \
            "        computeFlavourId: " + self.__flavor_name + "\n" \
            "        computeName: " + self.__name + "\n" \
            "        locationConstraints: \"\"\n" \
            "        mecAppDId: \"\"\n" \
            "        metadata:\n" \
            "        - key: ServiceId\n" \
            "          value: " + self.__ns_server_id + "\n" \
            "        - key: AbstractNfviPoPId\n" \
            "          value: \"" + self.__nfvi_pop_id + "\"\n" \
            "        - key: key-name\n" \
            "          value: " + self.__key_name + "\n" \
            "        reservationId: \"\"\n" \
            "        resourceGroupId: \"\"\n" \
            "        userData: \n" \
            "          content: \"\"\n" \
            "          method: CONFIG-DRIVE\n" \
            "        vcImageId: " + self.__image + "\n" + \
               self.__network_addresses + \
               self.__relationships + \
            "\n"

        return yaml

    def set_name(self, name):
        self.__name = name

    def set_image(self, image):
        self.__image = image

    def set_user_image(self, user_image):
        self.__user_image = user_image

    def set_flavor_name(self, flavor):
        self.__flavor_name = flavor

    def add_dependency(self, name):
        if len(self.__relationships) == 0:
            self.__relationships += "    relationships:\n"
        self.__relationships += ""\
        "    - type: cloudify.relationships.depends_on\n"\
        "      target: " + name + "\n"

    def add_network(self, port):

        ip_address = ""
        mac_address = ""
        floating_ip_address = ""

        if "ip_address" in port.keys():
            ip_address = port['ip_address']

        if "mac_address" in port.keys():
            mac_address = port['mac_address']

        if "floating_ip_address" in port.keys():
            floating_ip_address = port['floating_ip_address']

        if len(self.__relationships) == 0:
            self.__relationships += "    relationships:\n"
        if len(self.__network_addresses) == 0:
            self.__network_addresses += "        interfaceData:\n"

        self.__relationships += \
        "    - type: cloudify.relationships.connected_to\n" \
        "      target: net_" + port['network'] + "\n"
        self.__network_addresses += \
        "        - networkId: net_" + port['network'] + "\n" \
        "          macAddress: " + mac_address + "\n" \
        "          ipAddress: " + ip_address + "\n"

        if port['floatingIp'] == True:
            self.__network_addresses += \
            "          floatingIP: \"" + floating_ip_address + "\"\n"

    def set_ns_service_id(self, ns_service_id):
        self.__ns_server_id = ns_service_id

    def set_key_name(self, key_name):
        self.__key_name = key_name

class PrivateNetwork(object):

    def __init__(self):
        self.__yaml = ""
        self.__name = ""
        self.__object_name = ""
        self.__connect_to_router = ""
        self.__openstack_config = ""
        self.__allocation_pools = ""
        self.__private_network = ""
        self.__enable_gw = False
        self.__private_subnet_network = ""
        self.__dhcp_pool_start = ""
        self.__dhcp_pool_end = ""
        self.__gateway_ip = "null"
        self.__nfvi_pop_id = ""
        self.__ns_service_id = ""
        self.__network_type = "subnet"
        self.__intrapop_vlan = ""
        self.__address_pool = [0]
        self.__depend_on_network = ""

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config


    def set_nfvi_pop_id(self, nfvi_pop_id):
        self.__nfvi_pop_id = nfvi_pop_id

    def set_name(self, name):
        self.__name = name

    def set_object_name(self, object_name):
        self.__object_name = object_name

    def connect_to_router(self):
        self.__enable_gw = True

    def set_allocation_pools(self, start, end):
        self.__dhcp_pool_start = start
        self.__dhcp_pool_end = end

    def set_network(self, network):
        self.__private_network = network

    def set_gateway_ip(self, gateway_ip):
        self.__gateway_ip = gateway_ip

    def set_ns_service_id(self, ns_service_id):
        self.__ns_service_id = ns_service_id

    def set_type(self, network_type):
        self.__network_type = network_type

    def set_interpop_vlan(self, vlan):
        self.__intrapop_vlan = \
        "          - key: \"interpop_vlan\"\n" \
        "            value: \"" + str(vlan) + "\"\n"

    def set_address_pool(self, address_pool):
        self.__address_pool = address_pool

    def depend_on(self, depend_on_network):
        if depend_on_network is not None and depend_on_network != "":
            self.__depend_on_network = \
            "    relationships:\n" \
            "      - type: cloudify.relationships.depends_on\n" \
            "        target: " + depend_on_network + "\n"

    def get_yaml(self):
        self.__yaml = \
        "  net_" + self.__object_name + ":\n"\
        "    type: cloudify.mtp.subnet_vl\n" \
        "    properties:\n" \
        "      mtp_config: *mtp_config\n" \
        "      mtp_network:\n" \
        "        affinityOrAntiAffinityConstraints: \"null\"\n" \
        "        locationConstraints: \"null\"\n"\
        "        metadata:\n"\
        "        - key: ServiceId\n"\
        "          value: " + self.__ns_service_id + "\n"\
        "        - key: AbstractNfviPoPId\n"\
        "          value: " + self.__nfvi_pop_id + "\n"\
        "        networkResourceName: " + self.__name + "\n"\
        "        networkResourceType: " + self.__network_type + "\n" \
        "        reservationId: " + self.__name + "\n" \
        "        resourceGroupId: \"null\"\n" \
        "        typeNetworkData: ""\n" \
        "        typeNetworkPortData: \"\"\n" \
        "        typeSubnetData:\n" \
        "          addressPool: " + str(self.__address_pool) + "\n" \
        "          cidr: " + self.__private_network + "\n" \
        "          gatewayIp: " + self.__gateway_ip + "\n" \
        "          ipVersion: IPv4\n" \
        "          isDhcpEnabled: true\n" \
        "          metadata:\n" \
        "          - key: \"ip-floating-required\"\n" \
        "            value: \"" + str(self.__enable_gw) + "\"\n" \
        +  self.__intrapop_vlan +\
        "          networkId: \"null\"\n" \
        "          resourceId: \"null\"\n" \
        + self.__depend_on_network + \
        "\n\n"

        return self.__yaml




class Script(object):
    def __init__(self):
        self.__yaml = ""
        self.__name = ""
        self.__openstack_config = ""
        self.__contain_in = ""
        self.__depend_on = ""
        self.__startscript_yml = ""
        self.__stopscript_yml = ""
        self.__scripts_directory = ""
        self.__yaml_depend_on = ""

    def set_name(self, name):
        self.__name = name

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config

    def set_contain_in(self, contain_in):
        self.__contain_in = contain_in

    def set_depend_on(self, depend_on):
        self.__depend_on = depend_on
        if self.__depend_on != self.__contain_in:
            self.__yaml_depend_on = \
            "      - type: cloudify.relationships.depends_on\n"\
            "        target: " + self.__depend_on + "\n"
        else:
            self.__yaml_depend_on = ""

    def start_script(self, script):
        # save start script
        data = ""
        for row in script['script']:
            data += row + "\n"

        file_name = self.__contain_in + "_" + self.__depend_on + "_start.sh"
        file = open(self.__scripts_directory + "/" + file_name, 'w')
        file.write(data)
        file.close()
        args = ""
        for idx, (key, arg) in enumerate(script['args'].items()):
            args += arg
            if idx < (len(script['args']) - 1):
                args += ", "
        self.__startscript_yml = \
        "         start:\n"\
        "           implementation: scripts/" + file_name + "\n"\
        "           inputs:\n"\
        "             process:\n"\
        "               args:  [" + args + "]\n"\


    def stop_script(self, script):
#       save stop script
        data = ""
        for row in script['script']:
            data += row + "\n"

        file_name = self.__contain_in + "_" + self.__depend_on + "_stop.sh"
        file = open(self.__scripts_directory + "/" + file_name, 'w')
        file.write(data)
        file.close()
        args = ""
        for idx, (key, arg) in enumerate(script['args'].items()):
            args += arg
            if idx < (len(script['args']) - 1):
                args += ", "
        self.__stopscript_yml = \
        "         stop:\n"\
        "           implementation: scripts/" + file_name + "\n"\
        "           inputs:\n"\
        "             process:\n"\
        "               args:  [" + args + "]\n"

    def get_yaml(self):
        self.__yaml = \
        "  " + self.__name + ":\n"\
        "    type: cloudify.nodes.WebServer\n"\
        "    relationships:\n"\
        "      - type: cloudify.relationships.contained_in\n"\
        "        target: " + self.__contain_in + "\n" + \
        self.__yaml_depend_on + \
        "    interfaces:\n"\
        "      cloudify.interfaces.lifecycle:\n" \
        + self.__startscript_yml \
        + self.__stopscript_yml + "\n"
        return self.__yaml

    def set_file_name_blueprint(self, file_name):
#       creates directory for script
        blueprint_directory = os.path.dirname(file_name)
        self.__scripts_directory = blueprint_directory + "/scripts"
        if os.path.exists(self.__scripts_directory) is False:
            os.mkdir(self.__scripts_directory)

