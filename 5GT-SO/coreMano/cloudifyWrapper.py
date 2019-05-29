"""
File description
"""

# python imports
import datetime

from coreMano.cloudify_wrapper_lib.cloudify_rest_client.client import CloudifyClient
from coreMano.cloudify_wrapper_lib.cloudify_rest_client.exceptions import CloudifyClientError
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
        self.__nfvo_ip = host_ip
        self.__cloudify_client = CloudifyClient(
            host=self.__nfvo_ip,
            username=self.__user,
            password=self.__password,
            tenant=self.__tenant)


    def instantiate_ns(self, nsi_id, ns_descriptor, vnfds_descriptor, body, placement_info, resources):
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

        # creates tmp folder for blueprint
        if not os.path.exists(self.__blueprints_path):
            os.makedirs(self.__blueprints_path)
        os.makedirs(self.__blueprints_path + "/" + nsi_id)
        currentDT = datetime.datetime.now()
        string_date = currentDT.strftime("%Y_%m_%d_%H_%M_%S")
        path_to_blueprint = self.__blueprints_path + "/" + nsi_id + "/" + string_date
        blueprint_name = ns_descriptor['nsd']['nsdIdentifier'] + "_" +body.ns_instantiation_level_id
        #full path and name for blueprint

        blueprint_yaml_name_with_path = path_to_blueprint + "/" + blueprint_name + ".yaml"
        os.makedirs(path_to_blueprint)

        # set parameters for blueprint
        converter_to_yaml = ConverterNSDOpenstackYAML()
        converter_to_yaml.set_placement_info(placement_info)
        converter_to_yaml.set_nfvis_pop_info(self.get_nfvi_pop_info())
        converter_to_yaml.set_ns_instantiation_level_id(body.ns_instantiation_level_id)
        converter_to_yaml.set_ns_descriptor(ns_descriptor)
        converter_to_yaml.set_vnfds_descriptor(vnfds_descriptor)
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
            else:
                log_queue.put(["INFO", "CLOUDIFY_WRAPPER: Blueprint %s %s" % (blueprint_name, e)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Blueprint %s.yaml upload error %s " % (blueprint_name, e)])
            return None

        # deployment creation

        try:
            self.__cloudify_client.deployments.create(blueprint_name, nsi_id)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deployment %s creation started" % (nsi_id)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deployment creation error %s " % (e)])
            return None

        try:
            self.wait_for_deployment_execution(nsi_id)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deployment %s creation completed" % (nsi_id)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deployment creation error %s " % (e)])
            return None

        # deploying
        try:
            self.__cloudify_client.executions.start(nsi_id, "install")
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deploying %s started" % (nsi_id)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deploying %s error %s " % (nsi_id, e)])
            return None

        try:
            self.wait_for_deployment_execution(nsi_id)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Deploying %s completed" % (nsi_id)])
        except Exception as e:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: Deploying %s error %s " % (nsi_id, e)])
            return None

        nsi_sap = self.__cloudify_client.deployments.outputs.get(deployment_id=nsi_id)


        #
        # instances = self.__cloudify_client.node_instances.list(deployment_id=nsi_id)
        #
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

        # creates tmp folder for blueprint

        scale_ns_instantiation_level_id = self.extract_target_il(body)
        scale_ops = self.extract_scaling_info(ns_descriptor, current_df, current_il, scale_ns_instantiation_level_id)
        log_queue.put(["DEBUG", "scaling target il: %s" % (scale_ns_instantiation_level_id)])
        # placement_info = nsir_db.get_placement_info(nsi_id)
        if not os.path.exists(self.__blueprints_path):
            os.makedirs(self.__blueprints_path)
        os.makedirs(self.__blueprints_path + "/" + nsi_id, exist_ok=True)
        currentDT = datetime.datetime.now()
        string_date = currentDT.strftime("%Y_%m_%d_%H_%M_%S")
        path_to_blueprint = self.__blueprints_path + "/" + nsi_id + "/" + string_date
        blueprint_name = ns_descriptor['nsd']['nsdIdentifier'] + "_" + scale_ns_instantiation_level_id
        #full path and name for blueprint
        blueprint_yaml_name_with_path = path_to_blueprint + "/" + blueprint_name + ".yaml"
        os.makedirs(path_to_blueprint)


        # set parameters for blueprint
        converter_to_yaml = ConverterNSDOpenstackYAML()
        converter_to_yaml.set_placement_info(placement_info)
        converter_to_yaml.set_nfvis_pop_info(self.get_nfvi_pop_info())
        converter_to_yaml.set_ns_instantiation_level_id(scale_ns_instantiation_level_id)
        converter_to_yaml.set_ns_descriptor(ns_descriptor)
        converter_to_yaml.set_vnfds_descriptor(vnfds_descriptor)
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

