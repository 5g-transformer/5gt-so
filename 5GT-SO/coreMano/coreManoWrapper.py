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
    log_queue.put(["INFO", "In create Wrapper"])
    config = RawConfigParser()
    config.read("../../coreMano/coreMano.properties")
    config.optionxform = str  # case sensitive
    name = config.get("CoreMano", "name")
    host_ip = config.get("CoreMano", "ip")
    log_queue.put(["INFO", "In create Wrapper name %s, host_ip %s" % (name, host_ip)])
    # instanciate and return the MANO
    mano = None
    if name == "osm":
        log_queue.put(["INFO", "In create Wrapper, if osm"])
        release = config.get("OSM", "release")
        if release == "3":
            ro_ip = config.get("OSM", "ro_host")
        else:
            ro_ip = None
        # print "MANO: ", name, "release:", release
        log_queue.put(["INFO", "In create Wrapper name %s, host_ip %s, ro_ip %s, release %s" %
                       (name, host_ip, ro_ip, release)])
        mano = OsmWrapper(name, host_ip, ro_ip, release)
        log_queue.put(["INFO", "In create Wrapper, created osmWrapper"])
    if name == "cloudify":
        mano = CloudifyWrapper(name, host_ip)
    # log_queue.put(["INFO", "In create Wrapper, before return"])
    # log_queue.put(["INFO", "In create Wrapper, mano is %s" % mano])
    return mano
