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
Wrapper to be able to return an instance of the selected MANO, selection based on the properties file.
"""

# python imports
from six.moves.configparser import RawConfigParser

# project imports
from coreMano.osmWrapper import OsmWrapper
from coreMano.cloudifyWrapper import CloudifyWrapper
from nbi import log_queue


def createWrapper():
    """
    Instantiates and returns an instance of the coreMANO selected in the coreMano.properties file.
    All coreMano must implement the following methods (see description at the end of the file):
    def instantiate_ns(self, nsi_id, ns_descriptor, body, placement_info);
    def terminate_ns(self, nsi_id);
    """

    # read properties file and get MANO name and IP
    config = RawConfigParser()
    config.read("../../coreMano/coreMano.properties")
    name = config.get("CoreMano", "coreMano.name")
    host_ip = config.get("CoreMano", "coreMano.ip")

    # instanciate and return the MANO
    if name == "osm":
        mano = OsmWrapper(name, host_ip)
    if name == "cloudify":
        mano = CloudifyWrapper(name, host_ip)
    return mano

#     def instantiate_ns(self, nsi_id, ns_descriptor, body, placement_info):
#         """
#         Instanciates the network service identified by nsi_id, according to the infomation contained in the body and
#         placement info.
#         Parameters
#         ----------
#         nsi_id: string
#             identifier of the network service instance
#         ns_descriptor: dict
#             json containing the nsd and vnfd's of the network service retrieved from catalogue
#         body: http request body
#             contains the flavourId nsInstantiationLevelId parameters
#         placement_info: dict
#             result of the placement algorithm
#         Returns
#         -------
#         To be defined
#         """
#
#     def terminate_ns(self, nsi_id):
#         """
#         Terminates the network service identified by nsi_id.
#         Parameters
#         ----------
#         nsi_id: string
#             identifier of the network service instance
#         Returns
#         -------
#         To be defined
#         """
