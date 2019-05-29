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
This file contains the methods used by the /operation path of the NBI.
"""

# python imports
import connexion
import six

# swagger imports
from swagger_server.models.inline_response2001 import InlineResponse2001  # noqa: E501
from swagger_server import util
from swagger_server.models.http_errors import error404

# project imports
import sm.soe.soe as soe

# log
from nbi import log_queue


def get_operation_status(operationId):  # noqa: E501
    """Returns the status of an operation by its operation Id

     # noqa: E501

    :param operationId: ID of the operation to return its status
    :type operationId: str

    :rtype: InlineResponse2001
    """

    status = soe.get_operation_status(operationId)
    if status == 404:
        return error404("operationId not found")

    return {"status": status}
