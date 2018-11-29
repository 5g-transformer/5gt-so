# -*- coding: utf-8 -*-

"""
Copyright 2018 Pantelis Frangoudis, EURECOM

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
#################################################################
Translation between json formats
#################################################################
"""

import copy
import uuid

  
#####################################
# LLs - host edges
#####################################

def logical_link_to_internal(ll):
  """Translate the given logical link (host edge) to the internal format.
  
  Example input:
  {
    "LLid": "1234",
    "capacity": {
      "total": 10,
      "available": 2
    },
    "delay": 0.006,
    "source": {
      "id": "server_0_switch_0_pod_0",
      "GwIpAddress": "192.168.1.1"
    },
    "destination": {451
      "id": "server_0_switch_0_pod_1",
      "GwIpAddress": "192.168.1.2"
    }
  }
      
  Example output:
  {
    "id": "1234",
    "capacity": 10,
    "utilization": 8, 
    "delay": 0.006, 
    "source": "server_0_switch_0_pod_0", 
    "target": "server_0_switch_0_pod_1"
  }
  """
  ll_internal = {}
  ll_internal["id"] = ll["LLid"]
  ll_internal["capacity"] = float(ll["capacity"]["total"])
  ll_internal["utilization"] = float(ll["capacity"]["total"]) - float(ll["capacity"]["available"])
  ll_internal["delay"] = float(ll["delay"])
  ll_internal["source"] = ll["source"]["id"]
  ll_internal["target"] = ll["destination"]["id"]

  return ll_internal  


def logical_link_from_internal(ll):
  """Translate the given logical link to the external format.

  Example input:
  {
    "id": "1234",
    "capacity": 10,
    "utilization": 8, 
    "delay": 0.006, 
    "source": "server_0_switch_0_pod_0", 
    "target": "server_0_switch_0_pod_1"
  }
      
  Example output:
  {
    "LLid": "1234",
    "capacity": {
      "total": 10,
      "available": 2
    },
    "delay": 0.006,
    "source": {
      "id": "server_0_switch_0_pod_0",
      "GwIpAddress": ""
    },
    "destination": {
      "id": "server_0_switch_0_pod_1",
      "GwIpAddress": ""
    }
  }
  """
  ll_external = {}
  if "id" in ll:
    ll_external["LLid"] = ll["id"]
  else:
    # generate random link ID if it's not there
    ll_external["LLid"] = str(uuid.uuid4())
   
  ll_external["capacity"] = {}
  ll_external["capacity"]["total"] = ll["capacity"]
  if "utilization" in ll:
    ll_external["capacity"]["available"] = ll["capacity"] - ll["utilization"]
  else:
    ll_external["capacity"]["available"] = ll["capacity"]
  ll_external["delay"] = float(ll["delay"])  
  
  # gateway IP addresses are not supported by the GA
  ll_external["source"] = {
    "id": ll["source"],
    "GwIpAddress": ""
  }
  ll_external["destination"] = {
    "id": ll["target"],
    "GwIpAddress": ""
  }

  return ll_external

########################################
# NFVIPoP - host
########################################

def nfvipop_to_internal(pop):
  """Translate the given NFVI PoP information to the internal format.
  
  Example input:
  {
    "id": "popid",
    "location": {
      "center": {
        "longitude": 0,
        "latitude": 0
      },
      "radius": 0
    },
    "gw_ip_address": "192.168.1.1",
    "capabilities": {
      "cpu": 100,
      "ram": 1000,
      "storage": 10000,
      "bandwidth": 1
    },
    "availableCapabilities": {
      "cpu": 20,
      "ram": 100,
      "storage": 1000,
      "bandwidth": 0.2
    },
    "failure_rate": 0,
    "internal_latency": 0
  }
  Example ouput
  {
    "host_name": "popid", 
    "capabilities": {
      "storage": 1000, 
      "cpu": 16, 
      "memory": 128
    },
    "failure_rate": 0
  }

  """
  host = {}
  host["host_name"] = pop["id"]
  host["location"] = pop["location"] # copied as-is, ignored by GA
  host["gw_ip_address"] = pop["gw_ip_address"] # copied as-is, ignored by GA
  host["failure_rate"] = pop["failure_rate"]
  # we copy the "availableCapabilities" instead of the capabilities, since the latter
  # are only important for our algorithm
  host["capabilities"] = {
    "cpu": pop["availableCapabilities"]["cpu"],
    "memory": pop["availableCapabilities"]["ram"],
    "storage": pop["availableCapabilities"]["storage"],
    "bandwidth": pop["availableCapabilities"]["bandwidth"] # copied as-is, ignored by GA
  }
  return host


def nfvipop_from_internal(host):
  """Translate the given host/POP information to the external format.
  """
  pop = {}
  pop["id"] = host["host_name"]
  if "location" in host:
    pop["location"] = host["location"]
  else:
    pop["location"] = {}
  if "gw_ip_address" in host:
    pop["gw_ip_address"] = host["gw_ip_address"] # copied as-is, ignored by GA
  if "failure_rate" in host:
    pop["failure_rate"] = host["failure_rate"]
  else:
    pop["failure_rate"] = 0
  

  if "bandwidth" in host["capabilities"]:
    bw = host["capabilities"]["bandwidth"]
  else:
    bw = 0
  pop["capabilities"] = {
    "cpu": host["capabilities"]["cpu"],
    "ram": host["capabilities"]["memory"],
    "storage": host["capabilities"]["storage"],
    "bandwidth": bw
  }
  pop["availableCapabilities"] = copy.deepcopy(pop["capabilities"])
  return pop


########################################
# VNFs
########################################

def vnf_to_internal(ext):
  """Translate VNF information to the internal format.

  Example input:
  {
    "VNFid": "vnf1",
    "instances": 0,
    "location": {
      "center": {
        "longitude": 0,
        "latitude": 0
      },
      "radius": 0
    },
    "requirements": {
      "cpu": 0,
      "ram": 0,
      "storage": 0
    },
    "failure_rate": 0,
    "processing_latency": 4
  }

  Example output:
  {
    "vnf_name": "vnf1", 
    "processing_time": 4, 
    "requirements": {
      "storage": 10, 
      "cpu": 1, 
      "memory": 4
    },
    "failure_rate": 0
  }
  """
  internal = {}
  internal["vnf_name"] = ext["VNFid"]
  internal["processing_time"] = ext["processing_latency"]
  internal["failure_rate"] = ext["failure_rate"]
  internal["requirements"] = {
    "storage": ext["requirements"]["storage"],
    "memory": ext["requirements"]["ram"],
    "cpu": ext["requirements"]["cpu"]
  }
  internal["instances"] = ext["instances"] # ignored
  internal["location"] = ext["location"]
  return internal
  
  
def vnf_from_internal(internal):
  """Translate VNF information to the external format.
  """
  
  ext = {}
  ext["VNFid"] = internal["vnf_name"]
  ext["processing_latency"] = internal["processing_time"]
  if "failure_rate" in internal:
    ext["failure_rate"] = internal["failure_rate"]
  else:
    ext["failure_rate"] = 0

  ext["requirements"] = {
    "storage": internal["requirements"]["storage"],
    "ram": internal["requirements"]["memory"],
    "cpu": internal["requirements"]["cpu"]
  }
  
  if "instances" in internal:
    ext["instances"] = internal["instances"]
  else:
    ext["instances"] = 0

  if "location" in internal:
    ext["location"] = internal["location"]
  else:
    ext["location"] = {}

  return ext


########################################
# Costs
########################################


def vnf_cost_to_internal(ext):
  """Translate the given VNF *cost* information to the internal format.
  
  Example input:
  {
    "cost": 1,
    "vnfid": "vnf1",
    "NFVIPoPid": "h1"
  }
    
  Example output:
  {
    "vnf": "vnf1", 
    "host": "h1", 
    "cost": 1
  }
  """
  internal = {}
  internal["cost"] = ext["cost"]
  internal["vnf"] = ext["vnfid"]
  internal["host"] = ext["NFVIPoPid"]
  return internal

def vnf_cost_from_internal(internal):
  """Translate the given VNF cost information to the external format.

  Example input:  
  {
    "vnf": "vnf1", 
    "host": "h1", 
    "cost": 1
  }
  
  Example output:
  {
    "cost": 1,
    "vnfid": "vnf1",
    "NFVIPoPid": "h1"
  }
  """
  ext = {}
  ext["cost"] = internal["cost"]
  ext["vnfid"] = internal["vnf"]
  ext["NFVIPoPid"] = internal["host"]
  return ext

# ((Logical and virtual) link costs are not consider by the GA. They can be included in the 
# translated request, but they will be ignored by the GA

########################################
# VNF links
########################################

def vnf_link_to_internal(ext):
  """Translate the given VNF link information to the internal format.
  
  Example input:
  {
    "VLid": "123",
    "source": "vnf1",
    "destination": "vnf2",
    "required_capacity": 10,
    "traversal_probability": 0
  }

  # traversal probability may be ignored here
  # a second pass will be necessary in order to
  # build the struct necessary ("service")
    
  Example output:
  {
    "id": "123"
    "source": "vnf1", 
    "traffic": 10, 
    "target": "vnf2"
  }
  """
  internal = {}
  if "VLid" in ext:
    internal["id"] = ext["VLid"]
  internal["source"] = ext["source"]
  internal["target"] = ext["destination"]
  internal["traffic"] = ext["required_capacity"]

  return internal

def vnf_link_from_internal(internal):
  """
  Example input:
  {
    ["id": "123",]
    "source": "vnf1", 
    "traffic": 10, 
    "target": "vnf2"
  }

  Example output:
  {
    ["VLid": "123",]
    "source": "vnf1",
    "destination": "string",
    "required_capacity": 0,
    "traversal_probability": 1
  }
  """
  internal = {}
  if "id" in internal:
    ext["VLid"] = internal["id"]
  ext["source"] = internal["source"]
  ext["destination"] = internal["target"] 
  ext["required_capacity"] = internal["traffic"]
  ext["traversal_probability"] = 1 # tocheck
  return ext

########################################
# Network service
# (here we only take care of translating an nsd to the internal representation)
########################################

def network_service_to_internal(nsd):
  """Translate the given NSD to the internal representation.
  """
  service = {}
  service["service_name"] = nsd["id"] #see what to do w. service name
  if "max_latency" in nsd:
    service["max_latency"] = nsd["max_latency"]
  if "target_availability" in nsd:
    service["target_availability"] = nsd["target_availability"]
  if "max_cost" in nsd:
    service["max_cost"] = nsd["max_cost"]
  
  # now construct traversal probabilities
  # this has to be checked!!
  traversed_vnfs = {}
  for vl in nsd["VNFLinks"]:
    if float(vl["traversal_probability"]) < 1.0:
      traversed_vnfs[vl["destination"]] = vl["traversal_probability"]
    else:
      traversed_vnfs[vl["source"]] = 1.0
      traversed_vnfs[vl["destination"]] = 1.0
    
  
  service["traversed_vnfs"] = traversed_vnfs
  
  return service


def vnfs_from_nsd(nsd):
  """From the given nsd in the external fmt, translate and return the list
  of included VNFs.
  """
  vnfs = []
  for vnf in nsd["VNFs"]:
    vnfs.append(vnf_to_internal(vnf))
  return vnfs


def vnf_links_from_nsd(nsd):
  """From the given nsd in the external fmt, translate and return the list
  of included VLs.
  """
  VLs = []
  for link in nsd["VNFLinks"]:
    VLs.append(vnf_link_to_internal(link))
  return VLs


def translate_request(req):
  """Translate a received request from the external JSON fmt to 
  the internal one to pass on to the GA
  """

  internal = {}
  internal["ReqId"] = req["ReqId"]
  internal["callback"] = req["callback"]
  
  # NFVI
  
  nfvi = {}
  nfvi["hosts"] = []
  nfvi["host_edges"] = []
  nfvi["costs"] = []

  if "resource_types" not in req["nfvi"]:
    nfvi["resource_types"] = [""]
  else:
    nfvi["resource_types"] = ["cpu","memory","storage"]
  
  for pop in req["nfvi"]["NFVIPoPs"]:
    nfvi["hosts"].append(nfvipop_to_internal(pop))
  
  for he in req["nfvi"]["LLs"]:
    nfvi["host_edges"].append(logical_link_to_internal(he))

  for cost in req["nfvi"]["VNFCosts"]:
    nfvi["costs"].append(vnf_cost_to_internal(cost))

  internal["nfvi"] = nfvi

  # NSD
  
  nsd = {}
  nsd["vnf_edges"] = vnf_links_from_nsd(req["nsd"])
  nsd["vnfs"] = vnfs_from_nsd(req["nsd"])
  nsd["services"] = [network_service_to_internal(req["nsd"])] # normally there should be just one service in a request
  
  internal["nsd"] = nsd

  return internal


def _find_pop(pops, popid):
  """Find the pop with the given pop id in list which stores nfvipopid-[list] pairs
  """
  for pop in pops:
    if pop["NFVIPoPID"] == popid:
      return pop
  return None


def _find_link(links, llid):
  """Find the host (logical) link with the given LL id in list which stores LLid-[list] pairs
  """
  for link in links:
    if link["LLid"] == llid:
      return link
  return None


def _find_host_link(solution, h1, h2):
  """Find a host edge with the given endpoints in a solution object (in the internal representation).
  """
  for he in solution["host_edges"]:
    if he["source"] == h1 and he["target"] == h2:
      return he
  return None


##############################


def translate_solution(solution):
  """Translate the solution from the internal to the external JSON format.
  """
  ext = {}
  used_pops = []
  for v in solution["vnfs"]:
    if "place_at" in v and len(v["place_at"]) > 0:
      # If the VNF is placed at some hosts (in our case there are no VNF replicas to place)
      # find the host and add the VNF to its list (or add the host if not already in used_pops) 
      for pop in v["place_at"]: # there should be just one element in place_at normally
        p = _find_pop(used_pops, pop)
        if p is not None:
          p["mappedVNFs"].append(v["vnf_name"])
        else:
          used_pops.append({
            "NFVIPoPID": pop,
            "mappedVNFs": [v["vnf_name"]]
          })
  ext["usedNFVIPops"] = used_pops
  
  # Link mapping. We need two data structures:
  # - Used LLs
  # - Intra-PoP links
  # For each vnf link there is an object showing the source-dst host pair
  ext["usedLLs"] = []
  ext["usedVLs"] = []
  for ve in solution["vnf_edges"]:
    # If host_edge is missing from the VNF edge block, there's no
    # host edge mapping info, so we do nothing
    if "host_edge" in ve:
      # First check if both VNFs have been assigned at the same host
      if ve["host_edge"]["source"] == ve["host_edge"]["target"]:
        # intra-pop link. check if the NFVIPoP id is already there
        # the usedVLs structure maintains NFVPoP id - [list of mapped VLs] pairs
        p = _find_pop(ext["usedVLs"], ve["host_edge"]["source"])
        if p is not None:
          p["mappedVLs"].append(ve["id"]) # we assume that links between VNFs have IDs.
        else:
          ext["usedVLs"].append({
            "NFVIPoPID": ve["host_edge"]["source"],
            "mappedVLs": [ve["id"]]
          })
      else:
        # inter-PoP link
        host_link = _find_host_link(solution, ve["host_edge"]["source"], ve["host_edge"]["target"])
        if host_link is None or host_link["id"].endswith("-inv"):
          # search for a link in the reverse direction
          # and if it ends with -inv, this means that it is a reverse link added by the GA,
          #so just get the forward one
          host_link = _find_host_link(solution, ve["host_edge"]["target"], ve["host_edge"]["source"])
                    
        # The usedVLs data structure has LLid - [list of mapped VLs] pairs
        # NOTE: We assume that the input host graph has bidirectional edges.
        # In this case, internally, the algorithm adds reverse edges and assigns
        # them the same ID as the forward edge, with an "-inv" added at the end.
        # So, here, if an edge ends with -inv, we just remove it.
        # This is a temporary hack. If the input graph is directional, then we
        # should modify {ga,helpers}.py so that no reverse edges are added.
        l = _find_link(ext["usedLLs"], host_link["id"])
        if l is not None:
          l["mappedVLs"].append(ve["id"])
        else:
          ext["usedLLs"].append({
            "LLid": host_link["id"],
            "mappedVLs": [ve["id"]]
          })
      
  ext["totalLatency"] = 0
  ext["totalCost"] = 0
  if "solution_performance" in solution:
    ext["totalLatency"] = solution["solution_performance"]["latency"]["total"]
    ext["totalCost"] = solution["solution_performance"]["cost"]

  return ext

