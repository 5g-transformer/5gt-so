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
This file contains the methods used by the EWBI (network service federation).
"""


# python imports
import connexion
import six
from json import dumps, loads, load

# swagger imports
from swagger_server.models.federated_info import FederatedInfo  # noqa: E501
from swagger_server.models.inline_response2001 import InlineResponse2001  # noqa: E501
from swagger_server.models.inline_response2002 import InlineResponse2002  # noqa: E501
from swagger_server.models.interconnection_paths import InterconnectionPaths  # noqa: E501
from swagger_server import util
from swagger_server.models.http_errors import error400, error404

# project imports
import sm.crooe.crooe as crooe

# log
from nbi import log_queue


def federated_connection_paths(nsId, body):  # noqa: E501
    """Query towards the federated/provider domain to perform connections towards the local and other federate domains

     # noqa: E501

    :param nsId: nsId of the nested federated network service in federated domain
    :type nsId: str
    :param body: Identifier of the descriptor in the federated domain
    :type body: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        body = InterconnectionPaths.from_dict(connexion.request.get_json())  # noqa: E501
    requester = connexion.request.remote_addr
    pathInfo = crooe.set_federated_internested_connections_reply(nsId, body, requester)
    if pathInfo == 404:
        return error404("The requests coming from the federated domain is not returning valid information")
    log_queue.put(["DEBUG", "EWBI pathInfo: %s"%pathInfo])
    return {"pathInfo": pathInfo}


def federated_instance_info(nsId, body):  # noqa: E501
    """Query towards the federated/provider domain to know info about: CIDR/pools that have to be used/not used in the federated domain

     # noqa: E501

    :param nsId: nsId of the nested federated network service in federated domain
    :type nsId: str
    :param body: Identifier of the descriptor in the federated domain
    :type body: dict | bytes

    :rtype: InlineResponse2002
    """
    if connexion.request.is_json:
        body = FederatedInfo.from_dict(connexion.request.get_json())  # noqa: E501
    requester = connexion.request.remote_addr
    instanceInfo = crooe.get_federated_network_instance_info_reply(nsId, body.nsd_id, requester)
    if instanceInfo == 404:
        return error404("The requests coming from the local domain is not returning valid information")
    log_queue.put(["DEBUG", "EWBI instance_info: %s"%instanceInfo])
    return {"instanceInfo": instanceInfo} 


def federated_network_info(nsId, body):  # noqa: E501
    """Query towards the consumer/local domain about the information: CIDR/pools that have to be used/not used in the federated domain

     # noqa: E501

    :param nsId: nsId of the composite in consumer domain
    :type nsId: str
    :param body: Identifier of the descriptor in the federated domain
    :type body: dict | bytes

    :rtype: InlineResponse2001
    """
    if connexion.request.is_json:
        body = FederatedInfo.from_dict(connexion.request.get_json())  # noqa: E501
    requester = connexion.request.remote_addr
    networkInfo = crooe.get_federated_network_info_reply(nsId, body.nsd_id,requester)
    if networkInfo == 404:
        return error404("The requests coming from the federated domain is not returning valid information")
    log_queue.put(["DEBUG", "EWBI network_info: %s"%networkInfo])
    return {"networkInfo": networkInfo}
