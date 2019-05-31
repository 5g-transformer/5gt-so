import connexion
import six
import os
import sys

from swagger_server.models.pa_request import PARequest  # noqa: E501
from swagger_server.models.pa_response import PAResponse  # noqa: E501
from swagger_server import util

# Cluster matching dependencies
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(this_dir + '/../../../clustering/')
sys.path.append(this_dir + '/../../../cluster-matching/src')
from cluster import cluster
from garrota import best_garrote


def p_a_comp_get():  # noqa: E501
    """Retrieve a list of PA execution requests

    Retrieve the list of pending and completed PA requests. # noqa: E501


    :rtype: List[PAResponse]
    """
    return 'do some magic!'


def p_a_comp_post(PARequest):  # noqa: E501
    """Request the execution of a placement algorithm.

    Request the execution of a placement algorithm. The caller needs to implement a callback function and supply the relevant URI so that the PA can post there the result of its execution.- # noqa: E501

    :param PARequest: Placement algorithm request information.
    :type PARequest: dict | bytes

    :rtype: PAResponse
    """
    pa_req = None

    if connexion.request.is_json:
        pa_req = connexion.request.get_json()
        # PARequest = PARequest_.from_dict(connexion.request.get_json())  # noqa: E501

    pa_req = cluster(pa_req)

    return best_garrote(pa_req)


def p_a_comp_req_id_get(ReqId):  # noqa: E501
    """Retrieve a specific PA request

    Retrieve status information about a specific PA request. # noqa: E501

    :param ReqId: Unique request identifier.
    :type ReqId: str

    :rtype: PARequest
    """
    return 'do some magic!'
