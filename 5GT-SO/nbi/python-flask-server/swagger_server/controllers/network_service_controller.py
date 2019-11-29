# Copyright 2019 CTTC www.cttc.es
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
This file contains the methods used by the /ns path of the NBI (network service).
"""

# python imports
import connexion
import six
from json import dumps, loads, load

# swagger imports
from swagger_server.models.app_onboarding_reply import AppOnboardingReply  # noqa: E501
from swagger_server.models.app_onboarding_request import AppOnboardingRequest  # noqa: E501
from swagger_server.models.create_ns_identifier_request import CreateNsIdentifierRequest  # noqa: E501
from swagger_server.models.inline_response200 import InlineResponse200  # noqa: E501
from swagger_server.models.inline_response201 import InlineResponse201  # noqa: E501
from swagger_server.models.ns_info import NsInfo  # noqa: E501
from swagger_server.models.ns_instantiation_request import NsInstantiationRequest  # noqa: E501
from swagger_server.models.ns_onboarding_reply import NsOnboardingReply  # noqa: E501
from swagger_server.models.ns_scale_request import NsScaleRequest  # noqa: E501
from swagger_server.models.vnf_onboarding_reply import VnfOnboardingReply  # noqa: E501
from swagger_server.models.vnf_onboarding_request import VnfOnboardingRequest  # noqa: E501
from swagger_server import util
from swagger_server.models.http_errors import error400, error404

# project imports
import sm.soe.soe as soe
import sm.soe.soep as soep

# log
from nbi import log_queue


def create_ns_identifier(body):  # noqa: E501
    """Creates and returns a Network Service identifier (nsId)

     # noqa: E501

    :param body: Network Service information
    :type body: dict | bytes

    :rtype: InlineResponse201
    """
    log_queue.put(["INFO", "*****Time measure: NBI creation of ns_identifier"])
    if connexion.request.is_json:
        body = CreateNsIdentifierRequest.from_dict(connexion.request.get_json())  # noqa: E501
    nsId = soep.create_ns_identifier(body)
    if nsId == 404:
        return error404("nsdId not found")
    log_queue.put(["INFO", "*****Time measure: NBI returning operation ID instantiating ns at SM"])
    # TODO: debug, in return the 201 should not be needed but if it is missing the REST API returns a 200

    return {"nsId": nsId}, 201

def delete_appd(appdId, version):  # noqa: E501
    """Deletes the specified MEC application

     # noqa: E501

    :param appdId: ID of the MEC app descriptor
    :type appdId: str
    :param version: Version of the MEC app descriptor
    :type version: str

    :rtype: None
    """
    if soe.delete_appd(appdId, version):
        return {"deletedAppdInfoId": appdId}
    else:
        return error404("appdId not found")


def delete_nsd(nsdId, version):  # noqa: E501
    """Delete the onboarded network service referenced by nsdId

     # noqa: E501

    :param nsdId: ID of the network service descriptor
    :type nsdId: str
    :param version: Version of the network service descriptor
    :type version: str

    :rtype: InlineResponse201 + nsdId
    """
    if soe.delete_nsd(nsdId, version):
        return {"deletedNsdInfoId": nsdId}
    else:
        return error404("nsdId not found")


def delete_vnfd(vnfdId, version):  # noqa: E501
    """Deletes the specified virtual network function

     # noqa: E501

    :param vnfdId: ID of the virtual network function descriptor
    :type vnfdId: str
    :param version: Version of the virtual network function descriptor
    :type version: str

    :rtype: None
    """
    if soe.delete_vnfd(vnfdId, version):
        return {"deletedVnfdInfoId": vnfdId}
    else:
        return error404("vnfdId not found")

def instantiate_ns(nsId, body):  # noqa: E501
    """Instantiates the Network Service referenced by nsId

     # noqa: E501

    :param nsId: 
    :type nsId: str
    :param body: Network Service information
    :type body: dict | bytes

    :rtype: InlineResponse200
    """
    log_queue.put(["INFO", "*****Time measure: NBI starting instantiating ns at SM"])
    if connexion.request.is_json:
        body = NsInstantiationRequest.from_dict(connexion.request.get_json())  # noqa: E501
    requester = connexion.request.remote_addr
    operationId = soep.instantiate_ns(nsId, body, requester)
    # process errors
    if operationId == 400:
        return error400("network service is not in NOT_INSTANTIATED state")
    if operationId == 404:
        return error404("nsId not found, not a valid requester or nestedInstanceId cannot be shared")
    log_queue.put(["INFO", "*****Time measure: NBI returning operation ID instantiating ns at SM"])
    return {"operationId": operationId}

def onboard_appd(body):  # noqa: E501
    """Returns information of the onboarded MEC application

     # noqa: E501

    :param body: Information about the MEC APP descriptor
    :type body: dict | bytes

    :rtype: AppOnboardingReply
    """
    if connexion.request.is_json:
        body = AppOnboardingRequest.from_dict(connexion.request.get_json())  # noqa: E501
    appd_info = soep.onboard_appd(body)
    return appd_info

def onboard_nsd(body):  # noqa: E501
    """Returns information of the onboarded network service

     # noqa: E501

    :param body: The NSD descriptor
    :type body: 

    :rtype: NsOnboardingReply
    """
    if connexion.request.is_json:
        nsd_json = connexion.request.get_json()
    requester = connexion.request.remote_addr
    nsdInfoId = soep.onboard_nsd(nsd_json, requester)
    if nsdInfoId == 404:
        return error404("Network service descriptor has not been onboarded in the catalog")
    info = {"nsdInfoId": nsdInfoId}        
    return info

def onboard_vnfd(body):  # noqa: E501
    """Returns information of the onboarded virtual network function

     # noqa: E501

    :param body: Information about the VNF descriptor
    :type body: dict | bytes

    :rtype: VnfOnboardingReply
    """
    if connexion.request.is_json:
        body = VnfOnboardingRequest.from_dict(connexion.request.get_json())  # noqa: E501
    vnfd_info = soep.onboard_vnfd(body)
    return vnfd_info

def query_ns(nsId):  # noqa: E501
    """Returns information of the network service referenced by nsId

     # noqa: E501

    :param nsId: ID of the network service
    :type nsId: str

    :rtype: NsInfo
    """
    info = soep.query_ns(nsId)

    if info == 404:
        return error404("nsId not found")

    return {"queryNsResult": [info]}


def query_nsd(nsdId, version):  # noqa: E501
    """Returns information of the network service referenced by nsId

     # noqa: E501

    :param nsdId: ID of the network service descriptor
    :type nsdId: str
    :param version: Version of the network service descriptor
    :type version: str

    :rtype: object
    """
    nsd = soe.query_nsd(nsdId, version)

    if nsd == 404:
        return error404("nsdId/version not found")

    nsd["nsdId"] = nsd["nsd"]["nsdIdentifier"]
    nsd["name"] = nsd["nsd"]["nsdName"]
    nsd["designer"] = nsd["nsd"]["designer"]
    nsd["version"] = nsd["nsd"]["version"]
    nsd["operationalState"] = "ENABLED"
    nsd["usageState"] = "NOT_IN_USE"
    nsd["deletionPending"] = False
    nsd["userDefinedData"] = {}
    total_return = {"queryResult": [nsd]}

    return total_return


def query_vnfd(vnfdId, version):  # noqa: E501
    """Returns information of the virtual network function referenced by vnfId

     # noqa: E501

    :param vnfdId: ID of the virtual network function descriptor
    :type vnfdId: str
    :param version: Version of the virtual network function descriptor
    :type version: str

    :rtype: object
    """
    vnfd = soe.query_vnfd(vnfdId, version)

    if vnfd == 404:
        return error404("vnfdId/version not found")

    vnfd = {"vnfd": vnfd}
    vnfd["vnfdId"] = vnfd["vnfd"]["vnfdId"]
    vnfd["vnfProvider"] = vnfd["vnfd"]["vnfProvider"]
    vnfd["vnfProductName"] = vnfd["vnfd"]["vnfProductName"]
    vnfd["vnfSoftwareVersion"] = vnfd["vnfd"]["vnfSoftwareVersion"]
    vnfd["vnfdVersion"] = vnfd["vnfd"]["vnfdVersion"]
    vnfd["checksum"] = "TEST CHECKSUM"
    vnfd["softwareImage"] = []
    vnfd["operationalState"] = "ENABLED"
    vnfd["usageState"] = "NOT_IN_USE"
    vnfd["deletionPending"] = False
    total_return = {"queryResult": [vnfd]}
    return total_return

def query_appd(appdId, version):  # noqa: E501
    """Returns information of the MEC app function referenced by appdId

     # noqa: E501

    :param appdId: ID of the MEC app descriptor
    :type appdId: str
    :param version: Version of the MEC app descriptor
    :type version: str

    :rtype: object
    """
    appd = soe.query_appd(appdId, version)
    if appd == 404:
        return error404("appdId/version not found")
    appd = {"appd": appd}
    appd["appdId"] = appd["appd"]["appDId"]
    appd["appPackageInfoId" ] = appd["appd"]["appDId"]
    appd["version"] = appd["appd"]["appDVersion"]
    appd["provider"] = appd["appd"]["appProvider"]
    appd["name"] = appd["appd"]["appName"]
    appd["operationalState"] = "ENABLED"
    appd["usageState"] = "NOT_IN_USE"
    appd["deletionPending"] = False
    total_return = {"queryResult": [appd]}
    return total_return


def scale_ns(nsId, body):  # noqa: E501
    """Scales the Network Service referenced by nsId

     # noqa: E501

    :param nsId: Identifier of the NS to be scaled
    :type nsId: str
    :param body: Scale information
    :type body: dict | bytes

    :rtype: InlineResponse200
    """
    if connexion.request.is_json:
        body = NsScaleRequest.from_dict(connexion.request.get_json())  # noqa: E501
    # SCALING is done with 
    operationId = soep.scale_ns(nsId, body)
    # process errors
    if operationId == 400:
        return error400("network service is not in NOT_INSTANTIATED state")
    if operationId == 404:
        return error404("nsId not found or network service cannot be scaled")
    return {"operationId": operationId}



def terminate_ns(nsId):  # noqa: E501
    """Terminates the Network Service identified by nsId.

     # noqa: E501

    :param nsId: ID of the network service
    :type nsId: str

    :rtype: InlineResponse200
    """
    log_queue.put(["INFO", "*****Time measure: NBI starting termination ns at SM"])
    requester = connexion.request.remote_addr   
    operationId = soep.terminate_ns(nsId, requester)
    if operationId == 400:
        return error400("network service is not in INSTANTIATED or INSTANTIATING state")
    if operationId == 404:
        return error404("nsId not found or the requester has not authorization to perform this operation")
    log_queue.put(["INFO", "*****Time measure: NBI returning operation ID termination ns at SM"])
    return {"operationId": operationId}
