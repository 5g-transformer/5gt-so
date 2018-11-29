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
This file contains the methods used by the /ns path of the NBI (network service).
"""

# python imports
import connexion
import six

# swagger imports
from swagger_server.models.create_ns_identifier_request import CreateNsIdentifierRequest  # noqa: E501
from swagger_server.models.inline_response200 import InlineResponse200  # noqa: E501
from swagger_server.models.inline_response201 import InlineResponse201  # noqa: E501
from swagger_server.models.ns_info import NsInfo  # noqa: E501
from swagger_server.models.ns_instantiation_request import NsInstantiationRequest  # noqa: E501
from swagger_server import util
from swagger_server.models.http_errors import error400, error404

# project imports
import sm.soe.soe as soe

# log
from nbi import log_queue


def create_ns_identifier(body):  # noqa: E501
    """Creates and returns a Network Service identifier (nsId)

     # noqa: E501

    :param body: Network Service information
    :type body: dict | bytes

    :rtype: InlineResponse201
    """
    if connexion.request.is_json:
        body = CreateNsIdentifierRequest.from_dict(connexion.request.get_json())  # noqa: E501
    nsId = soe.create_ns_identifier(body)
    if nsId == 404:
        return error404("nsdId not found")
    # TODO: debug, in return the 201 should not be needed but if it is missing the REST API returns a 200
    return {"nsId": nsId}, 201


def instantiate_ns(nsId, body):  # noqa: E501
    """Instantiates the Network Service referenced by nsId

     # noqa: E501

    :param nsId: 
    :type nsId: str
    :param body: Network Service information
    :type body: dict | bytes

    :rtype: InlineResponse200
    """
    if connexion.request.is_json:
        body = NsInstantiationRequest.from_dict(connexion.request.get_json())  # noqa: E501
    operationId = soe.instantiate_ns(nsId, body)
    # process errors
    if operationId == 400:
        return error400("network service is not in NOT_INSTANTIATED state")
    if operationId == 404:
        return error404("nsId not found")

    return {"operationId": operationId}


def query_ns(nsId):  # noqa: E501
    """Returns information of the network service referenced by nsId

     # noqa: E501

    :param nsId: ID of the network service
    :type nsId: str

    :rtype: NsInfo
    """

    info = soe.query_ns(nsId)

    if info == 404:
        return error404("nsId not found")

    return info


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


def terminate_ns(nsId):  # noqa: E501
    """Terminates the Network Service identified by nsId.

     # noqa: E501

    :param nsId: ID of the network service
    :type nsId: str

    :rtype: InlineResponse200
    """
    operationId = soe.terminate_ns(nsId)
    if operationId == 400:
        return error400("network service is not in INSTANTIATED or INSTANTIATING state")
    if operationId == 404:
        return error404("nsId not found")
    return {"operationId": operationId}
