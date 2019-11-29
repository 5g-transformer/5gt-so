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
import datetime
from coreMano.cloudify_wrapper_lib.cloudify_rest_client.client import CloudifyClient
from coreMano.cloudify_wrapper_lib.cloudify_rest_client.exceptions import CloudifyClientError
from coreMano.cloudify_wrapper_lib.converter_nsd_mtp_yaml import ConverterNSDMTPYAML
from db.nsir_db import nsir_db
from nbi import log_queue
import time
import requests
from coreMano.cloudify_wrapper_lib.converter_nsd_openstack_yaml import *
import os

from requests.auth import HTTPBasicAuth




class CloudifyWrapper(object):
    """
    Class description
    """
    __instance = None
    __executions = {}

    ##########################################################################
    # PUBLIC METHODS                                                                                                       #
    ##########################################################################

    def __init__(self, name, host_ip):
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
        # TODO: use properties
        # read properties file and get MANO name and IP
        config = RawConfigParser()
        config.read("../../coreMano/coreMano.properties")
        self.__user = config.get("Cloudify", "user")
        self.__password = config.get("Cloudify", "password")
        self.__tenant = config.get("Cloudify", "tenant")
        self.__blueprints_path = "/tmp/CloudifyWrapper"
        self.__wrapper = config.get("Cloudify", "wrapper")
        self.__default_key_name = config.get("Cloudify", "default_key_name")
        self.__install_cloudify_agent = config.get("Cloudify", "install_cloudify_agent")
        self.__start_vlan = config.get("Cloudify", "vlan", fallback=None)
        self.__nfvo_ip = host_ip
        self.__cloudify_client = CloudifyClient(
            host=self.__nfvo_ip,
            username=self.__user,
            password=self.__password,
            tenant=self.__tenant)


    def instantiate_ns(self, nsi_id, ns_descriptor, vnfds_descriptor, body, placement_info, resources, nestedInfo):
    # def instantiate_ns(self, nsi_id, ns_descriptor, body, placement_info):
        """
        Instanciates the network service identified by nsi_id, according to the infomation contained in the body and
        placement info.
        Parameters
        ----------
        nsi_id: string
            identifier of the network service instance
        ns_descriptor: dict
            json containing the nsd and vnfd's of the network service retrieved from catalogue
        body: http request body
            contains the flavourId nsInstantiationLevelId parameters
        placement_info: dict
            result of the placement algorithm
        Returns
        -------
        To be defined
        """

        instantiationLevel = body.ns_instantiation_level_id
        # for composition/federation
        if nestedInfo:
            nested_descriptor = next(iter(nestedInfo))
            if len(nestedInfo[nested_descriptor]) > 1:
                # nested from a consumer domain
                nsId_tmp = nsi_id
            else:
                # nested local
                nsId_tmp = nsi_id + '_' + nested_descriptor
        else:
            nsId_tmp = nsi_id

        blueprint_name = nsId_tmp + "_" + ns_descriptor['nsd']['nsdIdentifier'] + "_" + instantiationLevel
        blueprints = self.__cloudify_client.blueprints.list(_include=['id'], id=[blueprint_name]).items
        if len(blueprints) == 0:
        # if True:
            log_queue.put(["INFO", "CLOUDIFY_WRAPPER: Blueprint %s will be created" % (blueprint_name)])
            # creates tmp folder for blueprint
            if not os.path.exists(self.__blueprints_path + "/" + nsId_tmp):
                os.makedirs(self.__blueprints_path + "/" + nsId_tmp)
            # os.makedirs(self.__blueprints_path + "/" + nsId_tmp)
            currentDT = datetime.datetime.now()
            string_date = currentDT.strftime("%Y_%m_%d_%H_%M_%S")
            path_to_blueprint = self.__blueprints_path + "/" + nsId_tmp + "/" + string_date

            #full path and name for blueprint

            blueprint_yaml_name_with_path = path_to_blueprint + "/" + blueprint_name + ".yaml"
            os.makedirs(path_to_blueprint)

            if self.__wrapper == "openstack":
                # set parameters for blueprint
                converter_to_yaml = ConverterNSDOpenstackYAML()
                converter_to_yaml.set_placement_info(placement_info)
                converter_to_yaml.set_nfvis_pop_info(self.get_nfvi_pop_info())
                converter_to_yaml.set_ns_instantiation_level_id(instantiationLevel)
                converter_to_yaml.set_ns_descriptor(ns_descriptor)
                converter_to_yaml.set_vnfds_descriptor(vnfds_descriptor)
                converter_to_yaml.set_ns_service_id(nsi_id)
                converter_to_yaml.parse()
                converter_to_yaml.sort_networks()
                converter_to_yaml.sort_servers()
                converter_to_yaml.generate_yaml(blueprint_yaml_name_with_path)

            if self.__wrapper == "mtp":
                converter_to_yaml = ConverterNSDMTPYAML()
                converter_to_yaml.set_placement_info(placement_info)
                converter_to_yaml.set_nested_info(nestedInfo)
                converter_to_yaml.set_nfvis_pop_info(self.get_nfvi_pop_info())
                converter_to_yaml.set_ns_instantiation_level_id(instantiationLevel)
                converter_to_yaml.set_ns_descriptor(ns_descriptor)
                converter_to_yaml.set_vnfds_descriptor(vnfds_descriptor)
                converter_to_yaml.set_ns_service_id(nsId_tmp)
                converter_to_yaml.set_start_vlan(self.__start_vlan)
                converter_to_yaml.default_key_name(self.__default_key_name)
                converter_to_yaml.install_cloudify_agent(self.__install_cloudify_agent)
                converter_to_yaml.parse()
                converter_to_yaml.sort_networks()
                converter_to_yaml.sort_servers()
                converter_to_yaml.generate_yaml(blueprint_yaml_name_with_path)

        # bluprint upload
        try:
            self.__cloudify_client.blueprints.upload(blueprint_yaml_name_with_path, blueprint_name)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Blueprint %s.yaml upload completed" % (nsId_tmp)])
        #Check if exists blueprint in cloudify
        except CloudifyClientError as e:
            if e.error_code == 'conflict_error':
                log_queue.put(["INFO", "CLOUDIFY_WRAPPER: Blueprint %s %s" % (blueprint_name, e)])
            else:
                log_queue.put(["INFO", "CLOUDIFY_WRAPPER: Blueprint %s %s" % (blueprint_name, e)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Blueprint %s.yaml upload error %s " % (blueprint_name, e)])
            return None

        # deployment creation

        try:
            self.__cloudify_client.deployments.create(blueprint_name, nsId_tmp)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deployment %s creation started" % (nsId_tmp)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deployment creation error %s " % (e)])
            return None

        try:
            self.wait_for_deployment_execution(nsId_tmp)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deployment %s creation completed" % (nsId_tmp)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deployment creation error %s " % (e)])
            return None

        # deploying
        try:
            self.__cloudify_client.executions.start(nsId_tmp, "install")
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deploying %s started" % (nsId_tmp)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deploying %s error %s " % (nsId_tmp, e)])
            return None

        try:
            self.wait_for_deployment_execution(nsId_tmp)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deploying %s completed" % (nsId_tmp)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deploying %s error %s " % (nsId_tmp, e)])
            return None

        nsi_sap = self.__cloudify_client.deployments.outputs.get(deployment_id=nsId_tmp)

        instances = self.__cloudify_client.node_instances.list(deployment_id=nsId_tmp)

        nodes = self.__cloudify_client.nodes.list(deployment_id=nsId_tmp)

        vnf_deployed_info = self.get_information_of_vnf(instances)
        nsir_db.save_vnf_deployed_info(nsId_tmp, vnf_deployed_info)

        vim_net_info = self.get_information_of_networks(nsId_tmp, instances, nodes, nestedInfo)
        nsir_db.save_vim_networks_info(nsId_tmp, vim_net_info)

        instantiation_output = {}
        instantiation_output["sapInfo"] = nsi_sap["outputs"]
        converted_output = self.convert_output(instantiation_output)
        return converted_output


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
        Returns
        -------
        To be defined
        """
        scale_ns_instantiation_level_id = self.extract_target_il(body)
        blueprint_name = nsi_id + "_" +ns_descriptor['nsd']['nsdIdentifier'] + "_" + scale_ns_instantiation_level_id
        blueprints = self.__cloudify_client.blueprints.list(_include=['id'], id=[blueprint_name]).items
        if len(blueprints) == 0:
            log_queue.put(["INFO", "CLOUDIFY_WRAPPER: Blueprint %s will be created" % (blueprint_name)])

            # creates tmp folder for blueprint

            scale_ops = self.extract_scaling_info(ns_descriptor, current_df, current_il, scale_ns_instantiation_level_id)
            log_queue.put(["DEBUG", "scaling target il: %s" % (scale_ns_instantiation_level_id)])
            # placement_info = nsir_db.get_placement_info(nsi_id)
            if not os.path.exists(self.__blueprints_path):
                os.makedirs(self.__blueprints_path)
            os.makedirs(self.__blueprints_path + "/" + nsi_id, exist_ok=True)
            currentDT = datetime.datetime.now()
            string_date = currentDT.strftime("%Y_%m_%d_%H_%M_%S")
            path_to_blueprint = self.__blueprints_path + "/" + nsi_id + "/" + string_date

            #full path and name for blueprint
            blueprint_yaml_name_with_path = path_to_blueprint + "/" + blueprint_name + ".yaml"
            os.makedirs(path_to_blueprint)


            if self.__wrapper == "openstack":
                # set parameters for blueprint
                converter_to_yaml = ConverterNSDOpenstackYAML()
                converter_to_yaml.set_placement_info(placement_info)
                converter_to_yaml.set_nfvis_pop_info(self.get_nfvi_pop_info())
                converter_to_yaml.set_ns_instantiation_level_id(scale_ns_instantiation_level_id)
                converter_to_yaml.set_ns_descriptor(ns_descriptor)
                converter_to_yaml.set_vnfds_descriptor(vnfds_descriptor)
                converter_to_yaml.set_ns_service_id(nsi_id)
                converter_to_yaml.parse()
                converter_to_yaml.sort_networks()
                converter_to_yaml.sort_servers()
                converter_to_yaml.generate_yaml(blueprint_yaml_name_with_path)

            if self.__wrapper == "mtp":
                converter_to_yaml = ConverterNSDMTPYAML()
                converter_to_yaml.set_placement_info(placement_info)
                # converter_to_yaml.set_nested_info(nestedInfo)
                converter_to_yaml.set_nfvis_pop_info(self.get_nfvi_pop_info())
                converter_to_yaml.set_ns_instantiation_level_id(scale_ns_instantiation_level_id)
                converter_to_yaml.set_ns_descriptor(ns_descriptor)
                converter_to_yaml.set_vnfds_descriptor(vnfds_descriptor)
                converter_to_yaml.set_ns_service_id(nsi_id)
                converter_to_yaml.set_start_vlan(self.__start_vlan)
                converter_to_yaml.default_key_name(self.__default_key_name)
                converter_to_yaml.install_cloudify_agent(self.__install_cloudify_agent)
                converter_to_yaml.parse()
                converter_to_yaml.sort_networks()
                converter_to_yaml.sort_servers()
                converter_to_yaml.generate_yaml(blueprint_yaml_name_with_path)

            # bluprint upload
            try:
                self.__cloudify_client.blueprints.upload(blueprint_yaml_name_with_path, blueprint_name)
                log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Blueprint %s.yaml upload completed" % (nsi_id)])
            #Check if exists blueprint in cloudify
            except CloudifyClientError as e:
                if e.error_code == 'conflict_error':
                    log_queue.put(["INFO", "CLOUDIFY_WRAPPER: Blueprint %s %s" % (blueprint_name, e)])
            except Exception as e:
                log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Blueprint %s.yaml upload error %s " % (blueprint_name, e)])
                return None
        else:
            log_queue.put(["INFO", "CLOUDIFY_WRAPPER: Blueprint %s exists in cloudify" % (blueprint_name)])


        # deployment update
        try:
            self.__cloudify_client.deployment_updates.update_with_existing_blueprint(nsi_id, blueprint_name)
            # self.__cloudify_client.deployment_updates.update(nsi_id, blueprint_yaml_name_with_path)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deployment %s update by %s started" % (nsi_id, blueprint_name)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deployment %s update by %s error %s " % (nsi_id, blueprint_name, e)])
            return None

        try:
            self.wait_for_deployment_execution(nsi_id)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Scale Deployment %s update by %s completed" % (nsi_id, blueprint_name)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Scale Deployment %s update by %s error %s " % (nsi_id, blueprint_name, e)])
            return None

        nsi_sap = self.__cloudify_client.deployments.outputs.get(deployment_id=nsi_id)
        instances = self.__cloudify_client.node_instances.list(deployment_id=nsi_id)
        nodes = self.__cloudify_client.nodes.list(deployment_id=nsi_id)
        vnf_deployed_info = self.get_information_of_vnf(instances)
        nsir_db.save_vnf_deployed_info(nsi_id, vnf_deployed_info)
        vim_net_info = self.get_information_of_networks(nsi_id, instances, nodes, None)
        nsir_db.save_vim_networks_info(nsi_id, vim_net_info)
        instantiation_output = {}
        instantiation_output["sapInfo"] = nsi_sap["outputs"]
        converted_output = self.convert_output(instantiation_output)
        return [converted_output, scale_ops]

    def extract_target_il(self, body):
        if (body.scale_type == "SCALE_NS"):
            return body.scale_ns_data.scale_ns_to_level_data.ns_instantiation_level


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

        # undeploying
        try:
            self.__cloudify_client.executions.start(nsi_id, "uninstall")
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deployment  %s uninstalling started" % (nsi_id)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deploying %s uninstalling error %s " % (nsi_id, e)])
            return None

        try:
            self.wait_for_deployment_execution(nsi_id)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deployment %s uninstalling completed" % (nsi_id)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deployment %s  uninstalling error %s " % (nsi_id, e)])
            return None

        # deployment deleting
        try:
            self.__cloudify_client.deployments.delete(nsi_id)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deployment %s deleting started" % (nsi_id)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deployment deleting error %s " % (e)])
            return None
        log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deployment %s deleting completed" % (nsi_id)])

    ##########################################################################
    # PRIVATE METHODS                                                                                                      #
    ##########################################################################

    def get_information_of_vnf(self, instances):
        # vnf_deployed_info = [{"name": "spr1",
        #                       "port_info": [{"ip_address": "192.168.3.12", "mac_address": "192.168.3.12"}]},
        #                      {"name": "spr2",
        #                       "port_info": [{"ip_address": "192.168.3.13", "mac_address": "192.168.3.13"}]}
        #                      ]
        vnf_deployed_info = []

        for instance in instances:
            if instance.runtime_properties.get('external_type') == "mtp_compute":
                net_interfaces = instance.runtime_properties.get('external_resource')['virtualNetworkInterface']
                vm_name = instance.runtime_properties.get('external_resource')['computeName']
                port_info = []

                for net_interface in net_interfaces.values():
                    dc = ""
                    for metadata in net_interface['metadata']:
                        if metadata['key'] == 'dc':
                            dc = str(metadata['value'])
                    port_info.append({"ip_address": net_interface['ipAddress'][0], "mac_address": net_interface['macAddress']})
                vnf_deployed_info.append({"name": vm_name, "port_info": port_info, "dc": dc})

        return vnf_deployed_info

    def get_information_of_networks(self, ns_id, instances, nodes, nestedInfo):
        # {"cidr": {"VideoData": "192.168.3.0/24"},
        # "name": {"VideoData": ['1']},
        # "vlan": {"VideoData": "30"},
        # "vlan": {"addressPool": [0]}}

        vim_net_info = {"cidr": {}, "name": {}, "vlan_id": {}, "addressPool": {}}

        for instance in instances:
            # pprint(node)
            if 'external_type' in instance['runtime_properties'].keys():
                if "subnet_vl" in instance['runtime_properties']['external_type']:
                    network_runtime_properties = instance['runtime_properties']
                    net_name = network_runtime_properties['external_resource']['networkData']['networkResourceName']
                    net_name = net_name.replace(ns_id + "_","")
                    if nestedInfo:
                        nested_descriptor = next(iter(nestedInfo))
                        network_mapping = nestedInfo[nested_descriptor][0]
                        for network_map in network_mapping:
                            for net_value, net_key in network_map.items():
                                if net_name == net_key:
                                    net_name = net_value
                                    break
                    net_cidr = network_runtime_properties['external_resource']['subnetData']['cidr']
                    address_pool = network_runtime_properties['external_resource']['subnetData']['addressPool']
                    vlan = 1
                    if ('SegmentationID' in network_runtime_properties['external_resource']['subnetData']['metadata']):
                        vlan = network_runtime_properties['external_resource']['subnetData']['metadata']['SegmentationID']
                    vim_net_info["cidr"].update({net_name : net_cidr})
                    vim_net_info["name"].update({net_name: ['1']})
                    vim_net_info["vlan_id"].update({net_name: vlan})
                    vim_net_info["addressPool"].update({net_name: address_pool})

        return vim_net_info

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
                if (scaling_sign > 0): #SCALE_OUT
                    scale_info["scaleVnfType"] = "SCALE_OUT"
                elif (scaling_sign < 0): #SCALE_IN
                    scale_info["scaleVnfType"] = "SCALE_IN"
                for ops in range (0, abs(scaling_sign)):
                    # scale_info["instanceNumber"] = str(current_il_info[key] + ops + 1) -> not needed instance number
                    # scaling operation are done one by one
                    # protection for scale_in operation: the final number of VNFs cannot reach 0
                    if not (scale_info["scaleVnfType"] == "SCALE_IN" and (current_il_info[key] - ops > 0) ):
                        scaling_il_info.append(scale_info)
        log_queue.put(["DEBUG", "Scale_il_info is: %s"%(scaling_il_info)])
        return scaling_il_info



    def get_nfvi_pop_info(self):
        # self.vim_info
        vim_info = {}
        config = RawConfigParser()
        config.optionxform = str
        config.read("../../coreMano/vim.properties")
        config.keys()
        nfvipops = {}
        vims = {}
        for key in config.keys():
            if str(key).startswith("NFVIPOP"):
                nfvipop_parametes = dict(config.items(key))
                nfvipops.update({nfvipop_parametes['nfviPopId']: nfvipop_parametes})

        number_of_vims = config.getint("VIM", "number")
        for i in range(1, number_of_vims + 1):
            vim = dict(config.items("VIM" + str(i)))
            vims.update({vim['vimId']:vim})

        for key, nfvipop in nfvipops.items():
            vim_id =  nfvipop['vimId']
            nfvipops[key]['vim'] = vims[vim_id]
        return nfvipops


    def convert_output(self, param):
        ret_obj = {}
        ret_obj['sapInfo'] = {}
        for level1_key, level2_value in param['sapInfo'].items():
            ret_obj['sapInfo'][level1_key] = []
            for level3_key, level3_value in level2_value.items():
                ret_obj['sapInfo'][level1_key].append({level3_key: level3_value})
        return ret_obj


    def wait_for_deployment_execution(self, deployment_id):
        while True:
            time.sleep(2)
            executions = self.__cloudify_client.executions.list(_include=['status'], deployment_id=deployment_id)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Checking status of deployment %s" % (deployment_id)])
            pending = False
            for execution in executions:
                if execution['status'] in ["failed"]:
                    log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deployment %s status failed"% (deployment_id)])
                    raise Exception("CLOUDIFY_WRAPPER: Deployment %s status failed"% (deployment_id))
                if execution['status'] in ["pending", "started"]:
                    pending = True
            if pending == False:
                break

    def get_execution(self, execution):
        """
        Retrieves the execution information from cloudify
        ----------
        execution: string
            identifier of the execution
        Returns
        -------
        Dictionary with the execution status
        """

        url = 'http://%s/api/v3.1/executions/%s' % (self.__nfvo_ip, execution)
        log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: get_execution:%s" % url])
        headers = {'Tenant': self.__tenant}
        response = requests.get(
            url,
            auth=HTTPBasicAuth(self.__user, self.__password),
            headers=headers,
        )
        return response.json()

