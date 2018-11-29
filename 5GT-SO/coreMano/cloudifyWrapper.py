
"""
File description
"""

# python imports
from logging import getLogger
from nbi import log_queue
import time
import requests
import json
from db.nsd_db.nsd_db import get_nsd_cloudify_id
from db.ns_db.ns_db import get_nsdId

from requests.auth import HTTPBasicAuth

from six.moves.configparser import RawConfigParser


# cloudify imports

# project imports

# get the logger


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
        self.user = config.get("Cloudify", "user")
        self.password = config.get("Cloudify", "password")
        self.tenant = config.get("Cloudify", "tenant")
        self.nfvo_ip = host_ip

    def instantiate_ns(self, nsi_id, ns_descriptor, body, placement_info):
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
        blueprint_id = self.get_blueprint_id(nsi_id, body)
        if self.create_deployment(nsi_id, blueprint_id):
            instantiation_output = self.create_install_workflow(nsi_id)
            if instantiation_output is not None:
                nsi_sap = self.get_deployment_sap(nsi_id)
                instantiation_output["sapInfo"] = nsi_sap
                return instantiation_output

            return instantiation_output

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
        operation_id = self.create_uninstall_workflow(nsi_id)
        if operation_id is not None:
            self.delete_deployment(nsi_id)

    ##########################################################################
    # PRIVATE METHODS                                                                                                      #
    ##########################################################################
    def wait_execution(self, execution):
        """
        Holds the execution until a task finishes in cloudify.
        Parameters
        ----------
        execution: string
            identifier of the execution
        Returns
        -------
        To be defined
        """
        log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: wait_execution:%s" % execution])
        execution_data = self.get_execution(execution)
        while execution_data["status"] not in ["terminated"]:
            time.sleep(5)
            execution_data = self.get_execution(execution)
            if execution_data["status"] == "failed":
                log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: wait_execution:%s" % execution])
                return False
        return True

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

        url = 'http://%s/api/v3.1/executions/%s' % (self.nfvo_ip, execution)
        log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: get_execution:%s" % url])
        headers = {'Tenant': self.tenant}
        response = requests.get(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            headers=headers,
        )
        return response.json()

    def get_nsd_parameters(self, nsd_id):
        # TODO
        return {}

    def create_deployment(self, nsi_id, blueprint_id):
        """
        Creates a deployment within cloudify
        Parameters
        ----------
        nsi_id: string
            identifier of the network service instance used as deployment id
        blueprint_id: string
            identifier of the cloudify bluprint matching the network service descriptor desired
        Returns
        -------
        boolean representing the successful operation
        """
        url = 'http://%s/api/v3.1/deployments/%s' % (self.nfvo_ip, nsi_id)
        headers = {
            'Content-Type': 'application/json',
            'Tenant': self.tenant,
        }
        querystring = {'_include': 'id'}
        # skip_plugin=json.dumps({'skip-plugins-validation':True})
        inputs = self.get_nsd_parameters(nsi_id)

        payload = {
            'blueprint_id': blueprint_id,
            'inputs': inputs,
            'visibility': 'tenant',
            'skip-plugins-validation': True
        }
        log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: create_deployment url:%s payload:%s" % (url, json.dumps(payload))])

        try:
            response = requests.put(
                url, auth=HTTPBasicAuth(self.user, self.password),
                headers=headers,
                params=querystring,
                json=payload,
            )
            if response.status_code != requests.codes.created:
                log_queue.put(
                    ["ERROR", "CLOUDIFY_WRAPPER: create_deploymen %s %s" % (response.status_code, response.reason)])
                return False
            else:
                log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: create_deployment completed"])
                return True
        except requests.exceptions.RequestException as e:
            log_queue.put(["ERROR", "CANNOT  connect to cloudify"])
            return False

    def create_install_workflow(self, nsi_id):
        """
        Triggers the install workflow within cloudify
        Parameters
        ----------
        nsi_id: string
            identifier of the network service instance used as deployment id

        Returns
        -------
        Dictionary with the operation_id or None if the operation fails
        """

        while self.pending_workflow(nsi_id):
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: waiting workflow:%s" % nsi_id])
            time.sleep(5)
        url_exec = 'http://%s/api/v3.1/executions' % (self.nfvo_ip)
        headers = {
            'Content-Type': 'application/json',
            'Tenant': self.tenant,
        }
        payload_exec = {
            'deployment_id': nsi_id,
            'workflow_id': 'install',
        }
        querystring = {'_include': 'id'}
        while self.pending_workflow(nsi_id):
            time.sleep(5)
            log_queue.put(["DEBUG", "CLOUDIFY_WRAPPER: Waiting for deployment creation:%s" % nsi_id])
        log_queue.put(
            ["DEBUG", "CLOUDIFY_WRAPPER: create_install_workflow url:%s payload:%s" % (url_exec, payload_exec)])
        response_exec = requests.post(
            url_exec,
            auth=HTTPBasicAuth(self.user, self.password),
            headers=headers,
            params=querystring,
            json=payload_exec,
        )
        if response_exec.status_code == requests.codes.created:
            operation_id = response_exec.json()["id"]
            self.__executions[nsi_id] = operation_id
            return {"operation_id": operation_id}
        else:
            log_queue.put(
                ["ERROR",
                 "CLOUDIFY_WRAPPER: create_install_workflow %s %s" % (response_exec.status_code, response_exec.reason)])
            return None

    def create_uninstall_workflow(self, nsi_id):
        """
        Triggers the uninstall workflow within cloudify
        Parameters
        ----------
        nsi_id: string
            identifier of the network service instance used as deployment id

        Returns
        -------
        TBD
        """
        wait_exec = True
        if nsi_id in self.__executions:
            wait_exec = self.wait_execution(self.__executions[nsi_id])

        if wait_exec:
            url_exec = 'http://%s/api/v3.1/executions' % (self.nfvo_ip)
            headers = {
                'Content-Type': 'application/json',
                'Tenant': self.tenant,
            }
            payload_exec = {
                'deployment_id': nsi_id,
                'workflow_id': 'uninstall',
            }
            querystring = {'_include': 'id'}
            response_exec = requests.post(
                url_exec,
                auth=HTTPBasicAuth(self.user, self.password),
                headers=headers,
                params=querystring,
                json=payload_exec,
            )
            if response_exec.status_code == requests.codes.created:
                operation_id = response_exec.json()["id"]
                self.__executions[nsi_id] = operation_id
                return operation_id
            else:
                log_queue.put(
                    ["ERROR", "CLOUDIFY_WRAPPER: create_uninstall_workflow %s %s" % (
                        response_exec.status_code, response_exec.reason)])
                return None
        else:
            return None

    def delete_deployment(self, deployment):
        """
        Deletes a cloudify deployment
        Parameters
        ----------
        deployment: string
           identifier of the network service instance used as deployment id

        Returns
        -------
        True or false depending if the operation was succesfull or not
        """

        url = 'http://%s/api/v3.1/deployments/%s' % (self.nfvo_ip, deployment)
        headers = {'content-type': 'application/json',
                   'Tenant': self.tenant}
        querystring = {'_include': 'id', 'ignore_live_nodes': True}
        wait_exec = True
        if deployment in self.__executions:
            wait_exec = self.wait_execution(self.__executions[deployment])

        if wait_exec:
            response = requests.delete(
                url,
                auth=HTTPBasicAuth(self.user, self.password),
                headers=headers,
                params=querystring,
            )
            if response.status_code != requests.codes.ok:
                log_queue.put(
                    ["ERROR", "CLOUDIFY_WRAPPER: create_uninstall_workflow %s %s" % (
                        response.status_code, response.reason)])
                return False
            else:
                return True
        else:
            return False

    def pending_workflow(self, deployment):
        """
       Checks if a deployment has pending workflows
       Parameters
       ----------
       deployment: string
           identifier of the network service instance used as deployment id

       Returns
       -------
       Boolean
       """
        url = 'http://%s/api/v3.1/executions' % self.nfvo_ip
        headers = {'Tenant': self.tenant}
        querystring = {'_include': 'id'}
        response = requests.get(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            headers=headers,
        )

        if response.status_code == requests.codes.ok:
            for current_workflow in response.json()["items"]:
                if current_workflow["deployment_id"] == deployment and current_workflow["status"] != "terminated":
                    return True
            return False
        else:
            log_queue.put(["ERROR", "CLOUDIFY_WRAPPER: pending_workflow %s" % deployment])
            return True

    def get_blueprint_id(self, nsi_id, body):
        """
        Checks if a deployment has pending workflows
        Parameters
        ----------
        deployment: string
            identifier of the network service instance used as deployment id

        Returns
        -------
        Boolean
        """
        nsd_id = get_nsdId(nsi_id)
        bp_id = get_nsd_cloudify_id(nsd_id)
        log_queue.put(
            ["DEBUG", "CLOUDIFY_WRAPPER: get_blueprint_id nsi_id:%s nsd_id:%s bp_id:%s" % (nsi_id, nsd_id, bp_id)])
        return bp_id

    def get_deployment_output(self, deployment):

        url = 'http://%s/api/v3.1/deployments/%s/outputs' % (self.nfvo_ip, deployment)
        headers = {'Tenant': self.tenant}
        querystring = {'_include': 'id,runtime_properties,state',
                       'deployment_id': deployment}
        log_queue.put(["DEBUG", "get_deployment_outputs url:%s headers:%s" % (url, headers)])
        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.user, self.password),
                headers=headers
            )
            output = response.json()
            log_queue.put(["DEBUG", "get_deployment_outputs output:%s output:%s" % (url, output)])
            return output
        except requests.exceptions.RequestException as e:
            log_queue.put(["ERROR", "Error retrieving cloudify deployment outputs"])
            return None

    def get_deployment_sap(self, deployment):
        log_queue.put(["DEBUG", "get_deployment_sap deployment:%s" % deployment])
        deployment_output = self.get_deployment_output(deployment)
        if deployment_output is not None:
            if "outputs" in deployment_output and "sapInfo" in deployment_output["outputs"]:
                return deployment_output["outputs"]["sapInfo"]
            else:
                log_queue.put(["ERROR", "Error retrieving SAP info from cloudify deployment outputs"])
                return None

        else:
            return None
