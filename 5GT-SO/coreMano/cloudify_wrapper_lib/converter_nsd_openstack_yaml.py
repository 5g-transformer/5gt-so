import copy
import os
from collections import OrderedDict
from configparser import RawConfigParser
config = RawConfigParser()
config.read("../../coreMano/coreMano.properties")
pa_pa_enable = config.get("PA", "pa_enable")
pa_pa_simulate = config.get("PA", "pa_simulate")


class ConverterNSDOpenstackYAML(object):
    def __init__(self):
        self.networks = {}
        self.servers = {}
        self.ns_descriptor = {}
        self.__vnfds_descriptor = {}
        self.__ns_instantiation_level_id = ""
        self.cloudify_blueprint = CloudifyBlueprint()
        self.__nfvis_pop_info = {}
        self.__map_network_sap = {}
        self.__output_object = {}
        self.__placement_info = {}

    def set_ns_instantiation_level_id(self, ns_instantiation_level_id):
        self.__ns_instantiation_level_id = ns_instantiation_level_id

    def set_vnfds_descriptor(self, vnfds_descriptor):
        self.__vnfds_descriptor = vnfds_descriptor

    def set_ns_descriptor(self, ns_descriptor):
        self.ns_descriptor = ns_descriptor

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
            # pprint(nsVirtualLink)
            ports = ns_virtual_link['cpdId']
            virtual_link_profile_id = ns_virtual_link['virtualLinkProfileId']
            network_name = self. getnetwork(virtual_link_profile_id)
            self.networks.update({network_name: {}})
            for port in ports:
                server[vnfd_id]['relations']['ports'].update({port: {'network': network_name}})
        return server

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
        third_octet = 1
        for server_name in self.servers.keys():
            vnfd = self.get_vnfd(server_name)
            vcpus = vnfd['virtualComputeDesc'][0]['virtualCpu']['numVirtualCpu']
            ram = vnfd['virtualComputeDesc'][0]['virtualMemory']['virtualMemSize']
            disk = vnfd['virtualStorageDesc'][0]['sizeOfStorage']
            sw_image = vnfd['vdu'][0]['swImageDesc']['swImage']
            user_image = vnfd['vdu'][0]['swImageDesc']['user_image']
            # sw_image = "cirros-0.3.5-x86_64-disk"
            flavor = {
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
                        if "number_ports" in self.networks[network_name]:
                            self.networks[network_name]['number_ports'] += 1
                        else:
                            self.networks[network_name].update({'number_ports': 10})

#                       skip if network contain pool
                        if "pool_start" in self.networks[network_name]:
                            continue
                        self.networks[network_name].update({'connect_to_Router': floating_ip_activated})
                        self.networks[network_name].update({'pool_start': "192.168." + str(third_octet) + ".10"})
                        self.networks[network_name].update({'ip_network': "192.168." + str(third_octet) + ".0/24"})
                        self.networks[network_name].update({"provider": False})
                        self.networks[network_name].update({'NFVIPoPID': "1"})
                        third_octet += 1
                        break

            # added NFVIPoPID to servers
            if pa_pa_enable == "true" or pa_pa_simulate == "true":
                for used_nfvi_pops in self.__placement_info['usedNFVIPops']:
                    if server_name in used_nfvi_pops['mappedVNFs']:
                        self.servers[server_name].update({'NFVIPoPID': used_nfvi_pops['NFVIPoPID']})

        # added NFVIPoPID to networks
        if pa_pa_enable == "true" or pa_pa_simulate == "true":
            for network in self.networks:
                for used_vl in self.__placement_info['usedVLs']:
                    if network in used_vl['mappedVLs']:
                        self.networks[network].update({'NFVIPoPID': used_vl['NFVIPoPID']})

        # PA add interpop network
            new_netwoks = {}
            vlan = 10
            for server_name, sever_value in self.servers.items():
                server_nfvi_po_pid = sever_value['NFVIPoPID']
                for port_name, port_value in sever_value['relations']['ports'].items():
                    for used_ll in self.__placement_info['usedLLs']:
                        if port_value['network'] in used_ll['mappedVLs']:
                            new_network_name = port_value['network'] + "_" + server_nfvi_po_pid
                            new_netwoks[new_network_name] = copy.deepcopy(self.networks[port_value['network']])
                            new_netwoks[new_network_name].update({"vlan": str(vlan)})
                            new_netwoks[new_network_name].update({"provider": True})
                            new_netwoks[new_network_name].update({'NFVIPoPID': server_nfvi_po_pid})
                            port_value['network'] = new_network_name
                            vlan += 1
            self.networks.update(new_netwoks)

            # PA delete old interpop network
            for used_ll in self.__placement_info['usedLLs']:
                for mappedVL in used_ll['mappedVLs']:
                    del self.networks[mappedVL]

        # set pool_end
        object_dict_network_number = {}
        for network_name, network_value in self.networks.items():
            local_network_name = network_name.rsplit('_', 1)[0]
            pool_start = network_value['pool_start']
            octets = pool_start.split('.')
            forth_octet = octets[3]
            if local_network_name in object_dict_network_number.keys():
                object_dict_network_number[local_network_name] += 1
                # if network_value['provider'] is True and network_value['connect_to_Router'] is True:
                    # octets[3] = str (object_dict_network_number[local_network_name])
                    # gateway_ip = ".".join(octets)
                    # network_value['gateway_ip'] = gateway_ip
            else:
                object_dict_network_number.update({local_network_name: 1})
                # if network_value['provider'] is True and network_value['connect_to_Router'] is True:
                #     octets[3] = "1"
                #     gateway_ip = ".".join(octets)
                #     network_value['gateway_ip'] = gateway_ip

            forth_octet_start = int(forth_octet) + (int(object_dict_network_number[local_network_name]) - 1) \
                                * int(network_value['number_ports'])
            forth_octet_end = int(forth_octet) + int(object_dict_network_number[local_network_name]) \
                              * int(network_value['number_ports']) - 1
            octets[3] = str(int(octets[3]) + int(network_value['number_ports'])
                            * int(object_dict_network_number[local_network_name]))
            octets[3] = str(forth_octet_start)
            network_value['gateway_ip'] = ".".join(octets)
            octets[3] = str(forth_octet_start + 1)
            pool_start = ".".join(octets)
            octets[3] = str(forth_octet_end)
            pool_end = ".".join(octets)
            network_value['pool_start'] = pool_start
            network_value['pool_end'] = pool_end

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
                            if arg_parts[0] == "vnf" and arg_parts[6] == "address":
                                for server_name_2, server_value_2 in self.servers.items():
#                                   find network by port
                                    for port_name, port_value in server_value_2['relations']['ports'].items():
                                        if arg_parts[5] == port_name:
                                            network_name = port_value['network']
                                            arg_return = "{ get_attribute: [" + arg_parts[1] + ", networks, " + \
                                                         network_name + "_network, 0] }"
                                            script_value['args'][arg_name] = arg_return
                            if arg_parts[0] == "vnf" and arg_parts[6] == "floating":
                                arg_return = "{get_attribute: [floating_ip_" + arg_parts[5] + ", floating_ip_address]}"
                                script_value['args'][arg_name] = arg_return

    def generate_yaml(self, file_name):
        router_name = "router_nfvi_pop_"
        security_group_name = "security_group_nfvi_pop_"
        keypair_name = "keypair_"
        script_name = "script_"

        self.cloudify_blueprint.add_start_comment("# \n # \n")
        self.cloudify_blueprint.add_tosca_version("cloudify_dsl_1_3")
        import_sources = ['http://www.getcloudify.org/spec/cloudify/4.3/types.yaml', 'plugin:cloudify-openstack-plugin']
        self.cloudify_blueprint.add_import(import_sources)

        if pa_pa_enable == "true" or pa_pa_simulate == "true":
            for used_nfvi_pops in self.__placement_info['usedNFVIPops']:
                nfvi_pop_id = used_nfvi_pops['NFVIPoPID']
                dsl_definiftion = OrderedDict()
                vim = self.__nfvis_pop_info[nfvi_pop_id]['vim']
                floating_network = vim['external_network']
                openstack_config = {
                    'username': vim['user'],
                    'password': vim['password'],
                    'tenant_name': vim['tenant_name'],
                    'auth_url': vim['auth_url'],
                    'region': vim['region']
                }
                auth_nfvi_pop = 'nfvi_pop_' + nfvi_pop_id
                openstack_config = OrderedDict(openstack_config)
                dsl_definiftion[auth_nfvi_pop] = openstack_config
                self.cloudify_blueprint.add_dsl_definiftions(dsl_definiftion)
        else:
            dsl_definiftion = OrderedDict()
            vim = self.__nfvis_pop_info["1"]['vim']
            floating_network = vim['external_network']
            openstack_config = {
                'username': vim['user'],
                'password': vim['password'],
                'tenant_name': vim['tenant_name'],
                'auth_url': vim['auth_url'],
                'region': vim['region']
            }
            auth_nfvi_pop = 'nfvi_pop_' + "1"
            openstack_config = OrderedDict(openstack_config)
            dsl_definiftion[auth_nfvi_pop] = openstack_config
            self.cloudify_blueprint.add_dsl_definiftions(dsl_definiftion)

        for server_name, server in self.servers.items():

            flavor_yaml = Falvor()
            flavor_yaml.set_openstack_config('nfvi_pop_' + server['NFVIPoPID'])
            flavor_yaml.set_vcpus(server['flavor']['vcpus'])
            flavor_yaml.set_ram(server['flavor']['ram'])
            flavor_yaml.set_disk(server['flavor']['disk'])
            flavor_yaml.set_name("flavor_" + server_name)

            server_yaml = Server()
            server_yaml.set_name(server_name)
            server_yaml.set_flavor("flavor_" + server_name)
            server_yaml.set_image(server['swImage'])
            server_yaml.set_user_image(server['userImage'])
            server_yaml.add_dependency("flavor_" + server_name)
            server_yaml.add_keypair(keypair_name + server['NFVIPoPID'])
            yaml_ports = []
            for port_name, port in server['relations']['ports'].items():
                server_yaml.add_port(port_name)
                yaml_port = Port()
                yaml_port.set_openstack_config('nfvi_pop_' + server['NFVIPoPID'])
                yaml_port.set_security_group_name(security_group_name + server['NFVIPoPID'])
                yaml_port.set_port_name(port_name)
                yaml_port.set_network_name(port['network'])
                if port['floatingIp'] is True:
                    vim = self.__nfvis_pop_info[server['NFVIPoPID']]['vim']
                    floating_network = vim['external_network']
                    yaml_port.add_floating_ip(floating_network)
                    sapd = self.__map_network_sap[port['network'].split("_")[0]]
#                   generate output object
                    if sapd not in self.__output_object:
                        self.__output_object[sapd] = {}
                    self.__output_object[sapd].update(
                        {server_name: "{get_attribute: [floating_ip_" + port_name + ", floating_ip_address]}"})
                yaml_ports.append(yaml_port)
            server_yaml.set_openstack_config('nfvi_pop_' + server['NFVIPoPID'])
            self.cloudify_blueprint.add_node_template(flavor_yaml.get_yaml())
            self.cloudify_blueprint.add_node_template(server_yaml.get_yaml())
            if "script" in server.keys():
                for script in server['script']:
                    script_yaml = Script()
                    script_yaml.set_name(script_name + script['target'] + "_" + server_name)
                    script_yaml.set_openstack_config('nfvi_pop_' + server['NFVIPoPID'])
                    script_yaml.set_contain_in(script['target'])
                    script_yaml.set_depend_on(server_name)
                    script_yaml.set_file_name_blueprint(file_name)
                    if "start" in script.keys():
                        script_yaml.start_script(script['start'])
                    if "start" in script.keys():
                        script_yaml.stop_script(script['stop'])
                    self.cloudify_blueprint.add_node_template(script_yaml.get_yaml())

            for yaml_port in yaml_ports:
                self.cloudify_blueprint.add_node_template(yaml_port.get_yaml())

        self.cloudify_blueprint.add_outputs(self.__output_object)

        for network_name, network in self.networks.items():
            if network['provider'] is True:
                provider_network = ProviderNetwork()
                provider_network.set_name(network_name)
                provider_network.set_allocation_pools(network['pool_start'], network['pool_end'])
                provider_network.set_network(network['ip_network'])
                provider_network.set_vlan(network['vlan'])
                provider_physical_network = self.__nfvis_pop_info[network['NFVIPoPID']]['vim']['vl_interface']
                provider_network.set_provider_physical_network(provider_physical_network)
                if network['connect_to_Router'] is True:
                    provider_network.set_gateway_ip(network['gateway_ip'])
                    provider_network.connect_to_router(router_name + network['NFVIPoPID'])
                else:
                    provider_network.set_gateway_ip("null")
                provider_network.set_openstack_config('nfvi_pop_' + network['NFVIPoPID'])
                self.cloudify_blueprint.add_node_template(provider_network.get_yaml())

            else:
                private_network = PrivateNetwork()
                private_network.set_name(network_name)
                private_network.set_allocation_pools(network['pool_start'], network['pool_end'])
                private_network.set_network(network['ip_network'])
                if network['connect_to_Router'] is True:
                    private_network.connect_to_router(router_name + network['NFVIPoPID'])
                private_network.set_openstack_config('nfvi_pop_' + network['NFVIPoPID'])
                self.cloudify_blueprint.add_node_template(private_network.get_yaml())

        public_network = PublicNetwork(floating_network, auth_nfvi_pop)
        self.cloudify_blueprint.add_node_template(public_network.get_yaml())

        if pa_pa_enable == "true" or pa_pa_simulate == "true":
            for used_nfvi_pops in self.__placement_info['usedNFVIPops']:
                nfvi_pop_id = used_nfvi_pops['NFVIPoPID']

                router = Router()
                router.set_name(router_name + nfvi_pop_id)
                router.set_openstack_config('nfvi_pop_' + nfvi_pop_id)
                router.set_external_network(floating_network)
                self.cloudify_blueprint.add_node_template(router.get_router())

                security_group = SecurityGroup()
                security_group.set_name(security_group_name + nfvi_pop_id)
                security_group.set_openstack_config('nfvi_pop_' + nfvi_pop_id)
                self.cloudify_blueprint.add_node_template(security_group.get_yaml())

                keypair = Keipair()
                keypair.set_name(keypair_name + nfvi_pop_id)
                keypair.set_openstack_config('nfvi_pop_' + nfvi_pop_id)
                self.cloudify_blueprint.add_node_template(keypair.get_yaml())

        else:
            router = Router()
            router.set_name(router_name + "1")
            router.set_openstack_config('nfvi_pop_' + "1")
            router.set_external_network(floating_network)
            self.cloudify_blueprint.add_node_template(router.get_router())

            security_group = SecurityGroup()
            security_group.set_name(security_group_name + "1")
            security_group.set_openstack_config('nfvi_pop_' + "1")
            self.cloudify_blueprint.add_node_template(security_group.get_yaml())

            keypair = Keipair()
            keypair.set_name(keypair_name + "1")
            keypair.set_openstack_config('nfvi_pop_' + "1")
            self.cloudify_blueprint.add_node_template(keypair.get_yaml())

        data = self.cloudify_blueprint.get_blueprint()
        file = open(file_name, 'w')
        file.write(data)
        file.close()

    def set_nfvis_pop_info(self, nfvis_pop_info):
        self.__nfvis_pop_info = nfvis_pop_info

    def set_placement_info(self, placement_info):
        self.__placement_info = placement_info

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
        self.__flavor = ""
        self.__image = ""
        self.__relationships = ""
        self.__openstack_config = ""
        self.__user_image = ""

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config

    def get_yaml(self):

        yaml = "  " + self.__name + ":\n" \
                 "    type: cloudify.openstack.nodes.Server\n" \
                 "    properties:\n" \
                 "      openstack_config: *" + self.__openstack_config + "\n" \
                 "      resource_id: " + self.__name + "\n" \
                 "      image: " + self.__image + "\n" \
                 "      flavor: " + self.__flavor + "\n" \
                 "      use_external_resource: false\n"\
                 "      create_if_missing: false\n"\
                 "      agent_config:\n" \
                 "        install_method: init_script\n" \
                 "        user: '" + self.__user_image + "'\n" + \
                 self.__relationships + "\n"


        return yaml

    def set_name(self, name):
        self.__name = name

    def set_image(self, image):
        self.__image = image

    def set_user_image(self, user_image):
        self.__user_image = user_image

    def set_flavor(self, flavor):
        self.__flavor = flavor

    def add_dependency(self, name):
        if len(self.__relationships) == 0:
            self.__relationships += "    relationships:\n"
        self.__relationships += ""\
        "    - type: cloudify.relationships.depends_on\n"\
        "      target: " + name + "\n"

    def add_keypair(self, name):
        if len(self.__relationships) == 0:
            self.__relationships += "    relationships:\n"
        self.__relationships += \
        "    - type: cloudify.openstack.server_connected_to_keypair\n"\
        "      target: " + name + "\n"

    def add_port(self, port):
        if len(self.__relationships) == 0:
            self.__relationships += "    relationships:\n"
        self.__relationships += \
        "    - type: cloudify.openstack.server_connected_to_port\n" \
        "      target: " + port + "\n"


class PublicNetwork(object):

    def __init__(self, name, openstack_config):
        self.__yaml = \
        "  " + name + ":\n" \
        "    type: cloudify.openstack.nodes.Network\n" \
        "    properties:\n" \
        "      use_external_resource: true\n" \
        "      resource_id: " + name + "\n" \
        "      openstack_config: *" + openstack_config + "\n\n"

    def get_yaml(self):
        return self.__yaml


class PrivateNetwork(object):
    def __init__(self):
        self.__yaml = ""
        self.__name = ""
        self.__connect_to_router = ""
        self.__openstack_config = ""
        self.__allocation_pools = ""
        self.__private_network = ""
        self.__enable_gw = False
        self.__private_subnet_network = ""
        self.__dhcp_pool_start = ""
        self.__dhcp_pool_end = ""
        self.__gateway_ip = "null"

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config

    def set_name(self, name):
        self.__name = name

    def connect_to_router(self, name):
        self.__enable_gw = True

        self.__connect_to_router =  \
        "    - type: cloudify.openstack.subnet_connected_to_router\n" \
        "      target: " + name

    def set_allocation_pools(self, start, end):
        self.__dhcp_pool_start = start
        self.__dhcp_pool_end = end

    def set_network(self, network):
        self.__private_network = network

    def get_yaml(self):
        if self.__dhcp_pool_start != "":
            if self.__enable_gw is False:
                self.__allocation_pools = \
                "               allocation_pools:\n"\
                "               - start: " + self.__dhcp_pool_start + "\n"\
                "                 end: " + self.__dhcp_pool_end + "\n"
            else:
                self.__allocation_pools = \
                "        allocation_pools:\n"\
                "        - start: " + self.__dhcp_pool_start + "\n"\
                "          end: " + self.__dhcp_pool_end + "\n"

        if self.__enable_gw is False:
            self.__private_subnet_network = "" \
            "  " + self.__name + "_subnet:\n"\
            "    type: cloudify.openstack.nodes.Subnet\n"\
            "    properties:\n"\
            "      openstack_config: *" + self.__openstack_config + "\n"\
            "      resource_id: " + self.__name + "_subnet\n" \
            "      use_external_resource: false\n" \
            "      create_if_missing: false\n" \
            "    interfaces:\n"\
            "       cloudify.interfaces.lifecycle:\n"\
            "         create:\n"\
            "           inputs:\n"\
            "             args:\n"\
            "               gateway_ip: " + self.__gateway_ip + "\n"\
            "               cidr: " + self.__private_network + "\n"\
            "               ip_version: 4\n" \
                                            + self.__allocation_pools + \
            "       cloudify.interfaces.validation:\n"\
            "         creation:\n"\
            "           inputs:\n"\
            "             args:\n"\
            "               gateway_ip: " + self.__gateway_ip + "\n"\
            "               cidr: " + self.__private_network + "\n"\
            "               ip_version: 4\n" \
                                            + self.__allocation_pools + \
            "    relationships:\n"\
            "    - type: cloudify.relationships.contained_in\n"\
            "      target: " + self.__name + "_network\n"

        else:
            self.__private_subnet_network = \
            "  " + self.__name + "_subnet:\n"\
            "    type: cloudify.openstack.nodes.Subnet\n"\
            "    properties:\n"\
            "      use_external_resource: false\n" \
            "      create_if_missing: false\n" \
            "      subnet:\n"\
            "        cidr: " + self.__private_network + "\n"\
            "        ip_version: 4\n" \
            + self.__allocation_pools + \
            "      openstack_config: *" + self.__openstack_config + "\n"\
            "      resource_id: " + self.__name + "_subnet\n"\
            "    relationships:\n"\
            "    - type: cloudify.relationships.contained_in\n"\
            "      target: " + self.__name + "_network\n" \
            + self.__connect_to_router + "\n"

        self.__yaml =  \
        "  " + self.__name + "_network:\n"\
        "    type: cloudify.openstack.nodes.Network\n"\
        "    properties:\n"\
        "      openstack_config: *" + self.__openstack_config + "\n"\
        "      resource_id: " + self.__name + "_network\n" \
        "      use_external_resource: false\n" \
        "      create_if_missing: false\n" \
        "\n" + \
        self.__private_subnet_network + "\n"

        return self.__yaml


class ProviderNetwork(object):
    def __init__(self):
        self.__yaml = ""
        self.__name = ""
        self.__connect_to_router = ""
        self.__openstack_config = ""
        self.__allocation_pools = ""
        self.__enable_gw = False
        self.__subnet_network = ""
        self.__provider_network = ""
        self.__vlan = ""
        self.__provider_physical_network = ""
        self.__dhcp_pool_start = ""
        self.__dhcp_pool_end = ""
        self.__gateway_ip = "null"
        self.__is_set_gw = False

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config

    def set_provider_physical_network(self, physical_interface):
        self.__provider_physical_network = physical_interface



    def connect_to_router(self, name):
        self.__enable_gw = True
        self.__connect_to_router =  \
        "    - type: cloudify.openstack.subnet_connected_to_router\n" \
        "      target: " + name

    def set_gateway_ip(self, gateway_ip):
        self.__is_set_gw = True
        self.__gateway_ip = gateway_ip

    def set_name(self, name):
        self.__name = name

    def set_vlan(self, vlan):
        self.__vlan = vlan

    def set_allocation_pools(self, start, end):
        self.__dhcp_pool_start = start
        self.__dhcp_pool_end = end

    def set_network(self, network):
        self.__provider_network = network

    def get_yaml(self):

        if self.__dhcp_pool_start != "":
            if self.__is_set_gw is True:
                self.__allocation_pools = \
                "               allocation_pools:\n"\
                "               - start: " + self.__dhcp_pool_start + "\n"\
                "                 end: " + self.__dhcp_pool_end + "\n"
            else:
                self.__allocation_pools = \
                "        allocation_pools:\n"\
                "        - start: " + self.__dhcp_pool_start + "\n"\
                "          end: " + self.__dhcp_pool_end + "\n"

        if self.__enable_gw is False and self.__gateway_ip == "null":
            self.__subnet_network = "" \
            "  " + self.__name + "_subnet:\n"\
            "    type: cloudify.openstack.nodes.Subnet\n"\
            "    properties:\n"\
            "      openstack_config: *" + self.__openstack_config + "\n"\
            "      resource_id: " + self.__name + "_subnet\n"\
            "    interfaces:\n"\
            "       cloudify.interfaces.lifecycle:\n"\
            "         create:\n"\
            "           inputs:\n"\
            "             args:\n"\
            "               gateway_ip: " + self.__gateway_ip + "\n"\
            "               cidr: " + self.__provider_network + "\n"\
            "               ip_version: 4\n" \
                                    + self.__allocation_pools + \
            "       cloudify.interfaces.validation:\n"\
            "         creation:\n"\
            "           inputs:\n"\
            "             args:\n"\
            "               gateway_ip: " + self.__gateway_ip + "\n"\
            "               cidr: " + self.__provider_network + "\n"\
            "               ip_version: 4\n" \
                                    + self.__allocation_pools + \
            "    relationships:\n"\
            "    - type: cloudify.relationships.contained_in\n"\
            "      target: " + self.__name + "_network\n"

        if self.__enable_gw is True and self.__gateway_ip != "null":
            self.__subnet_network = "" \
            "  " + self.__name + "_subnet:\n"\
            "    type: cloudify.openstack.nodes.Subnet\n"\
            "    properties:\n"\
            "      openstack_config: *" + self.__openstack_config + "\n"\
            "      resource_id: " + self.__name + "_subnet\n"\
            "    interfaces:\n"\
            "       cloudify.interfaces.lifecycle:\n"\
            "         create:\n"\
            "           inputs:\n"\
            "             args:\n"\
            "               gateway_ip: " + self.__gateway_ip + "\n"\
            "               cidr: " + self.__provider_network + "\n"\
            "               ip_version: 4\n" \
                                    + self.__allocation_pools + \
            "       cloudify.interfaces.validation:\n"\
            "         creation:\n"\
            "           inputs:\n"\
            "             args:\n"\
            "               gateway_ip: " + self.__gateway_ip + "\n"\
            "               cidr: " + self.__provider_network + "\n"\
            "               ip_version: 4\n" \
                                    + self.__allocation_pools + \
            "    relationships:\n"\
            "    - type: cloudify.relationships.contained_in\n"\
            "      target: " + self.__name + "_network\n"\
             + self.__connect_to_router + "\n"

        if self.__enable_gw is True and self.__is_set_gw == False:
            self.__subnet_network = \
            "  " + self.__name + "_subnet:\n"\
            "    type: cloudify.openstack.nodes.Subnet\n"\
            "    properties:\n"\
            "      subnet:\n" \
            "        cidr: " + self.__provider_network + "\n"\
            "        ip_version: 4\n" \
            + self.__allocation_pools + \
            "      openstack_config: *" + self.__openstack_config + "\n"\
            "      resource_id: " + self.__name + "_subnet\n"\
            "    relationships:\n"\
            "    - type: cloudify.relationships.contained_in\n"\
            "      target: " + self.__name + "_network\n" \
            + self.__connect_to_router + "\n"

        self.__yaml = "" \
        "  " + self.__name + "_network:\n"\
        "    type: cloudify.openstack.nodes.Network\n"\
        "    properties:\n"\
        "      openstack_config: *" + self.__openstack_config + "\n"\
        "      use_external_resource: false\n"\
        "      resource_id: " + self.__name + "_network\n"\
        "    interfaces:\n"\
        "       cloudify.interfaces.lifecycle:\n"\
        "         create:\n"\
        "           inputs:\n"\
        "             args:\n"\
        "                provider:network_type: vlan\n"\
        "                provider:physical_network: " + self.__provider_physical_network + "\n"\
        "                provider:segmentation_id: " + self.__vlan + "\n"\
        "\n" + \
                      self.__subnet_network + "\n"

        return self.__yaml


class Port(object):
    def __init__(self):
        self.__yaml = ""
        self.__relation_float_ip = ""
        self.__float_ip = ""
        self.__network = ""
        self.__security_group_name = "security_group_vnf"
        self.__openstack_config = ""
        self.__port_name = ""

    def set_security_group_name(self, security_group_name):
        self.__security_group_name = security_group_name

    def set_port_name(self, name):
        self.__port_name = name

    def get_port_name(self):
        return self.__port_name

    def get_yaml(self):
        self.__yaml = \
        "  " + self.__port_name + ":\n"\
        "    type: cloudify.openstack.nodes.Port\n"\
        "    properties:\n"\
        "      openstack_config: *" + self.__openstack_config + "\n"\
        "      resource_id: " + self.__port_name + "\n"\
        "      use_external_resource: false\n"\
        "      create_if_missing: false\n"\
        "    relationships:\n"\
        "    - type: cloudify.relationships.contained_in\n"\
        "      target: " + self.__network + "_network\n"\
        "    - type: cloudify.relationships.depends_on\n"\
        "      target: " + self.__network + "_subnet\n"\
        "    - type: cloudify.openstack.port_connected_to_security_group\n"\
        "      target: " + self.__security_group_name + "\n" \
        + self.__relation_float_ip + "\n" + \
        self.__float_ip

        return self.__yaml

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config

    def set_network_name(self, name):
        self.__network = name

    def add_floating_ip(self, network_name):
        self.__relation_float_ip = \
        "    - type: cloudify.openstack.port_connected_to_floating_ip\n"\
        "      target: floating_ip_" + self.__port_name + "\n"\

        self.__float_ip = "" \
        "  floating_ip_" + self.__port_name + ":\n"\
        "    type: cloudify.openstack.nodes.FloatingIP\n"\
        "    properties:\n"\
        "      openstack_config: *" + self.__openstack_config + "\n"\
        "      resource_id: floating_ip_" + self.__port_name + "\n"\
        "      use_external_resource: false\n" \
        "      create_if_missing: false\n" \
        "      floatingip:\n"\
        "        floating_network_name: " + network_name + "\n\n"


class Router(object):

    def __init__(self):
        self.__yaml = ""
        self.__name = ""
        self.__gw = ""
        self.__openstack_config = ""
        self.__external_network = ""

    def set_name(self, name):
        self.__name = name

    def set_gw(self, gw):
        self.__gw = gw

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config

    def set_external_network(self, name):
        self.__external_network = name

    def get_router(self):
        self.__yaml =  \
        "  " + self.__name + ":\n"\
        "   type: cloudify.openstack.nodes.Router\n"\
        "   properties:\n"\
        "     openstack_config: *" + self.__openstack_config + "\n"\
        "     resource_id: " + self.__name + "\n"\
        "     use_external_resource: false\n"\
        "     create_if_missing: false\n"\
        "   relationships:\n"\
        "   - type: cloudify.relationships.connected_to\n"\
        "     target: " + self.__external_network + "\n\n"
        return self.__yaml


class SecurityGroup(object):
    def __init__(self):
        self.__yaml = ""
        self.__name = ""
        self.__openstack_config = ""

    def set_name(self, name):
        self.__name = name

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config

    def get_yaml(self):
        self.__yaml = \
        "  " + self.__name + ":\n"\
        "    type: cloudify.openstack.nodes.SecurityGroup\n"\
        "    properties:\n"\
        "      openstack_config: *" + self.__openstack_config + "\n"\
        "      use_external_resource: true\n"\
        "      create_if_missing: true\n"\
        "      security_group:\n"\
        "        name: " + self.__name + "\n"\
        "        description: generic security group\n"\
        "      rules:\n"\
        "      - remote_ip_prefix: 0.0.0.0/0\n"\
        "        protocol: TCP\n"\
        "      - remote_ip_prefix: 0.0.0.0/0\n"\
        "        protocol: UDP\n"\
        "      - remote_ip_prefix: 0.0.0.0/0\n"\
        "        protocol: ICMP\n"\
        "        port_range_min: null\n"\
        "        port_range_max: null\n\n"
        return self.__yaml


class Falvor(object):
    def __init__(self):
        self.__yaml = ""
        self.__name = ""
        self.__openstack_config = ""
        self.__vcpus = "1"
        self.__ram = "1"
        self.__disk = "1"
        self.__swap = "0"
        self.__ephemeral = "0"

    def set_name(self, name):
        self.__name = name

    def set_vcpus(self, vcpus):
        self.__vcpus = vcpus

    def set_ram(self, ram):
        self.__ram = int(ram) * 1000

    def set_disk(self, disk):
        self.__disk = disk

    def set_swap(self, swap):
        self.__swap = swap

    def set_ephemeral(self, ephemeral):
        self.__ephemeral = ephemeral

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config

    def get_yaml(self):
        self.__yaml = \
        "  " + self.__name + ":\n"\
        "    type: cloudify.openstack.nodes.Flavor\n" \
        "    properties:\n" \
        "      openstack_config: *" + self.__openstack_config + "\n"\
        "      use_external_resource: true\n"\
        "      create_if_missing: true\n"\
        "      flavor:\n" \
        "        vcpus: " + str(self.__vcpus) + "\n" \
        "        ram: " + str(self.__ram) + "\n" \
        "        disk: " + str(self.__disk) + "\n" \
        "        swap: " + str(self.__swap) + "\n" \
        "        ephemeral: " + str(self.__ephemeral) + "\n" \
        "        is_public: true\n" \
        "      resource_id: " + self.__name + "\n\n"
        return self.__yaml


class Keipair(object):
    def __init__(self):
        self.__yaml = ""
        self.__name = ""
        self.__openstack_config = ""

    def set_name(self, name):
        self.__name = name

    def set_openstack_config(self, openstack_config):
        self.__openstack_config = openstack_config

    def get_yaml(self):
        self.__yaml = \
        "  " + self.__name + ":\n"\
        "    type: cloudify.openstack.nodes.KeyPair\n"\
        "    properties:\n"\
        "      use_external_resource: true\n"\
        "      create_if_missing: true\n"\
        "      resource_id: " + self.__name + "\n"\
        "      private_key_path: '" + self.__name + ".pem'\n"\
        "      openstack_config: *" + self.__openstack_config + "\n\n"
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



