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
Some utility functions for constraint checking, transforming 
between full solution objects <--> chromosomes, etc.
#################################################################
"""

import logging
from gene import Gene
from chromosome import Chromosome
from haversine import haversine
import time

def in_range(hloc, vloc):
  """Check if hloc (NFVIPoP location) lays within vloc (desired VNF location range).
  """
  d = haversine( 
        (float(hloc["center"]["latitude"]), float(hloc["center"]["longitude"])), 
        (float(vloc["center"]["latitude"]), float(vloc["center"]["longitude"])), 
        unit='km'
    )
  if d < vloc["radius"]:
    return True
  return False
  
def check_host_capacity_constraint(solution, h):
  """ Check if any capacity constraint is violated on a host.

  For the given host h, this function will check if the current
  placement of VNFs on it violates any of the given resource
  capacity constraints. Solution is assumed to be a full scenario
  object (i.e., including all resource types, vnfs, host info, etc.,
  as well as "place_at" fields for hosts).
  """

  # get the names/ids of all VNFs placed at h
  vnfs = []
  for v in solution['vnfs']:
    if "place_at" in v and v["place_at"] is not None:
      if v["place_at"][0] == h["host_name"]:
        vnfs.append(v)

  # for each resource type, do the capacity check
  for r in solution["resource_types"]:
    if get_host_available_capacity(solution, h, r) < 0:
      logging.warn(r + " capacity exceeded on host " + str(h["host_name"]) + ": " + str(get_host_available_capacity(solution, h, r)))
      return False

  return True


def get_host_available_capacity(solution, h, r):
  """Return the available capacity at host h for resource r.
  """
  
  # get the names/ids of all VNFs placed at h
  vnfs = []
  for v in solution['vnfs']:
    if "place_at" in v and v["place_at"]:
      if v["place_at"][0] == h["host_name"]:
        vnfs.append(v)

  # Capacity check for resource type r
  sum_consumed = 0
  capacity = h["capabilities"][r]
  for v in vnfs:
    sum_consumed += v["requirements"][r]
  
  return capacity - sum_consumed


def check_if_placement_allowed(solution, h, v):
  """Check if VNF v is allowed to be placed at host h. v and h are strings with VNF/host names
  
  This check takes place by considering the host-vnf-cost tuples.
  If there is no such tuple for the host-vnf pair, we assume it's not
  allowed to place the host there.
  """
  
  for c in solution["costs"]:
    if c["host"] == h and c["vnf"] == v:
      return True
  return False

def check_mec_constraints(solution):
  """ Check if MEC constraint is violated.

  For the given host h, this function will check if the current
  placement of VNFs on it violates any of the given resource
  capacity constraints. Solution is assumed to be a full scenario
  object (i.e., including all resource types, vnfs, host info, etc.,
  as well as "place_at" fields for hosts).
  """

  for h in solution["hosts"]:
    mec_capable_host = h["capabilities"]["mec"]
    
    # get the names/ids of all VNFs placed at h
    vnfs = []
    for v in solution['vnfs']:
      if "place_at" in v and v["place_at"] is not None:
        if v["place_at"][0] == h["host_name"]:
          if "mec" in v["requirements"] and v["requirements"]["mec"] and not mec_capable_host:
            return False
  return True

def check_location_constraints(solution):
  for v in solution["vnfs"]:
    if "location" not in v:
      # No location info about VNF, we can place it anywhere
      continue
    else:
      vloc = v["location"]
      
    if "place_at" in v and v["place_at"] is not None:
      hname = v["place_at"][0] 
      h = filter(lambda x: x.get("host_name") == hname, solution["hosts"])
      hloc = h[0]["location"]

    if not in_range(hloc, vloc):
      return False
  return True

def check_if_there_is_space(solution, v):
  """Check if there exists a host where v fits and is allowed to be placed.
  """

  for h in solution["hosts"]:
    h_passed_the_test = True
    for r in solution["resource_types"]:
      if get_host_available_capacity(solution, h, r) < v["requirements"][r] or (not h["capabilities"]["mec"] and v["requirements"]["mec"]):
        # There's at least one resource type for which v does not fit h
        h_passed_the_test = False
        break
      if not check_if_placement_allowed(solution, h["host_name"], v["vnf_name"]):
        # The VNF is not allowed to be placed here
        h_passed_the_test = False
        break
    if h_passed_the_test:
      # Stop at the first host that has enough capacity
      # (and maybe return it in case we're interested in using this function
      # in a first-fit algorithm)
      return h
  return None


def check_global_feasibility(scenario):
  """Check if there is overall capacity to host the requested VNFFG, plus some
  other initial constraint checks.
  
  This function performs some basic initial feasibility checks.
  - Checks if for each resource there is enough capacity over all hosts.
  - Checks if the sum of processing latencies on its own exceeds
  the delay threshold for any of the services included in the scenario
  - Checks if there are requirements for MEC and at least one host supports it.
  - Checks that for each VNF, there's at least one VNFIPoP that satisfies the
  location constraint, if any.
  """
  for r in scenario["resource_types"]:
    requirements = 0
    capacity = 0
    mec_requirements = 0
    mec_capacity = 0
    for h in scenario["hosts"]:
      capacity += h["capabilities"][r]
      if h["capabilities"]["mec"]:
        mec_capacity += h["capabilities"][r]
    for v in scenario["vnfs"]:
      requirements += v["requirements"][r]
      if v["requirements"]["mec"]:
        mec_requirements += v["requirements"][r]
    if requirements > capacity or mec_requirements > mec_capacity:
      logging.info("Global feasilbility check: The requested capacity is not available.")
      return False
  
  # For each VNF with location constraints, check if there's at least an NFVIPoP
  # in range.
  for v in scenario["vnfs"]:
    # No location constraints to apply
    if "location" not in v or not v["location"]:
      continue
    else:
      vloc = v["location"]

    exists_host_in_range = False
    for h in scenario["hosts"]:
      if "location" not in h:
        continue
      else:
        hloc = h["location"]
      if in_range(hloc, vloc) and check_if_placement_allowed(scenario, h["host_name"], v["vnf_name"]):
        exists_host_in_range = True
        break
    if not exists_host_in_range:
      # Went over all hosts but not is in range
      logging.info("Global feasilbility check: Location constraint not attainable.")
      return False

  # check if for each VNF there's at least one host that has space, is
  # allowed to host it, and has MEC capabilities if necessary.
  for v in scenario["vnfs"]:
    if not check_if_there_is_space(scenario, v):
      logging.info("Global feasilbility check: No host has the required capabilities.")
      return False

  for s in scenario["services"]:
    traversed_vnfs = s["traversed_vnfs"]
    # Sum of processing latencies across all VNFs of the service
    dproc = 0
    for vname in traversed_vnfs:
      v = filter(lambda x: x.get("vnf_name") == vname, scenario["vnfs"])[0]
      dproc += v["processing_time"]

    if dproc > s["max_latency"]:
      # The VNFs of the service have more processing delay than the service's constraint
      # (even ignoring link latencies)
      logging.info("Global feasilbility check: Latency constraint not attainable.")
      return False
    return True


def get_host_edge(solution, vedge):
  """Return the host edge corresponding to the VNF edge.
  
  Return the host edge corresponding to the v1->v2 link. 
  If any of the two VFNs is not yet placed, return None.
  v1 and v2 are VNF names
  """

  v1 = filter(lambda x: x.get("vnf_name") == vedge["source"], solution["vnfs"])
  # trick to work around the case for VNF links with no destination (hack--to re-check)
  if v1:
    v1 = v1[0]
  v2 = filter(lambda x: x.get("vnf_name") == vedge["target"], solution["vnfs"])
  if v2:
    v2 = v2[0]
  # find source host
  if "place_at" in v1 and v1["place_at"] is not None:
    src = v1["place_at"][0]
  else:
    src = None

  if "place_at" in v2 and v2["place_at"] is not None:
    dst = v2["place_at"][0]
  else:
    dst = None
  
  if src is None or dst is None:
    return None
    
  for edge in solution["host_edges"]:
    if edge["source"] == src and edge["target"] == dst:
      return edge

  return None

def get_mapped_vedge_endpoints(solution, vedge):
  """Return the hosts to which the VL has been mapped.
  """
  v1 = filter(lambda x: x.get("vnf_name") == vedge["source"], solution["vnfs"])
  # trick to work around the case for VNF links with no destination (hack--to re-check)
  if v1:
    v1 = v1[0]
  v2 = filter(lambda x: x.get("vnf_name") == vedge["target"], solution["vnfs"])
  if v2:
    v2 = v2[0]
  # find source host
  if "place_at" in v1 and v1["place_at"] is not None:
    src = v1["place_at"][0]
  else:
    src = None

  if "place_at" in v2 and v2["place_at"] is not None:
    dst = v2["place_at"][0]
  else:
    dst = None
  
  return (src, dst)

def find_reverse_edge(solution, hedge):
  src = hedge["source"]
  dst = hedge["target"]
  for e in solution["host_edges"]:
    if e["source"] == dst and e["target"] == src:
      return e
  return None

def check_link_capacity_constraints(solution):
  """Check if a potential solution violates the link capacity constraint.
  
  For each edge with v as a source or destination, we check if 
  the corresponding edge in the underlying host graph has enough capacity.
  
  To do so, we first reset all link utilization values. Then we iterate over
  VNF edges, look up the corresponding host edges and update their util. values.
  If we come across an edge whose utilization is > its capacity, the solution
  is considered infeasible.
  """
  for hedge in solution["host_edges"]:
    hedge["utilization"] = 0
  
  # Here we'll do a trick. Since foreach edge in the scenario file we
  # add another edge in the opposite direction with the same capacity,
  # we "mirror" the utilization of the two edges
  for vedge in solution["vnf_edges"]:
    hedge = get_host_edge(solution, vedge)
    if hedge:
      hedge["utilization"] += float(vedge["traffic"])
      # find inverse edge and add the traffic to its utilization
      hedge_rev = find_reverse_edge(solution, hedge)      
      hedge_rev["utilization"] += float(vedge["traffic"])
      if hedge["utilization"] > hedge["capacity"] or hedge_rev["utilization"] > hedge_rev["capacity"]:
        return False
    else:
      # if no host edge exists and they're not placed on the same host, 
      # check if there is a path between the two hosts
      (s,d) = get_mapped_vedge_endpoints(solution, vedge)
      
      if s is None or d is None:
        # Nothing to do, corresponds to cornercase of VL with just one endpoint
        continue
      
      if s != d:
        path = get_shortest_path(solution, s, d, vedge["traffic"])
        if not path:
          # No path exists with the necessary available capacity
          return False
        for e in path:
          e["utilization"] += float(vedge["traffic"])
          # do the same as before for each edge of the path
          e_rev = find_reverse_edge(solution, e)      
          e_rev["utilization"] += float(vedge["traffic"])
          # this check is probably no necessary, since the check has already been
          # carried out by the shortest path algorithm
          if e["utilization"] > e["capacity"] or e_rev["utilization"] > e_rev["capacity"]:
            return False

  return True

def show_host_link_status(solution):
  """Returns a string showing the capacity and link utilization for all
  host edges for a given solution.
  """
  retval = ""
  for hedge in solution["host_edges"]:
    u = 0
    if "utilization" in hedge:
      u = hedge["utilization"]
    retval += "Edge " + hedge["source"] + "->" + hedge["target"] + " (utilization/capacity): " + str(u) + "/" + str(hedge["capacity"]) + "\n"
  return retval


# TODO: Check if the use of traversed_vnfs is correct. Maybe we need a different
# representation for P(v2|v1,s). How about, e.g., VNFs that are reachable over
# multiple paths??
def get_solution_delay(solution, s, processing_delay=False):
  """Calculates the overall delay of a specific placement for a specific service.
  
  This function takes into account VNF-level processing delays,
  as well as link-associated ones. For now, we assume tha n(s,v) = 1.
  s is the service name (string).
  """
  service = filter(lambda x: x.get("service_name") == s, solution["services"])[0]
  traversed_vnfs = service["traversed_vnfs"]
  # Sum of processing latencies across all VNFs of the service
  dproc = 0

  for vname in traversed_vnfs:
    v = filter(lambda x: x.get("vnf_name") == vname, solution["vnfs"])[0]
    dproc += v["processing_time"]*traversed_vnfs[vname]
  
  # Sum of link latencies.
  # How it's calculated:
  # - For each VNFFG edge v1->v2, check the "traversed_vnf" value for the
  # edge destination and use this as P(v2|v1)
  dnwk = 0.0
  for vedge in solution["vnf_edges"]:
    hedge = get_host_edge(solution, vedge)
    if hedge:
      hlat = hedge["delay"]
    else:
      (s, d) = get_mapped_vedge_endpoints(solution, vedge)
      if s == d:
        # If two VNFs are placed on the same host, it could be that
        # there's no self-edge in the scenario file (this is a reasonable 
        # assumption), in other words placing VNFs on the same host 
        # has no delay overhead).
        hlat = 0.0
      else:
        # No direct edge between the two hosts. So, check if there's a path 
        # connecting the two hosts. If so, sum the link latencies of the path. 
        # Note that this check should take place after the link capacity check 
        # has been carried out since here we ignore link capacities and we might
        # as well end up selecting a low-latency path without the necessary capacity.

        hlat = 0.0
        if s is not None and d is not None:
          path = get_shortest_path(solution, s, d)
          # A path should always exist. Otherwise, this would have been detected
          # in the link capacity check. This check is heuristic since the data
          # might eventually follow a different path (e.g., due to not enough
          # available capacity). Also, this step ignores the processing latency
          # in intermediate notes since we assume that they are just forwarding
          # traffic and not doing any service-level processing.
          for e in path:
            hlat += e["delay"]

    # There could be the case that for a specific service the vedge destination
    # does not appear in traversed_vnfs. This means that the probability
    # to go from v1 -> v2 is zero  
    if vedge["target"] not in traversed_vnfs:
      probability = 0
    else:
      probability = float(traversed_vnfs[vedge["target"]])
    dnwk += probability*hlat
  
  if processing_delay:
    return dproc + dnwk 
  else:
    return dnwk


def check_delay_constraints(solution):
  """Check if the delay constraint is respected for all services.
  """
  
  # check if there's an edge mapped to a link that cannot support it
  for ve in solution["vnf_edges"]:
    hedge = get_host_edge(solution, ve)
    if hedge is not None and ve["latency"] < hedge["delay"]:
      return False

  for s in solution["services"]:
    # for constraint checking, we have to take into account processing delays, too
    latency = get_solution_delay(solution, s["service_name"], True)
    if  latency > s["max_latency"]:
      logging.warn("Max delay constraint violated for service " + s["service_name"] + " (latency/max): " + str(latency) + "/" + str(s["max_latency"]))
      return False
  return True


def get_solution_cost(solution):
  """Calculate the cost of a solution.
  
  We assume the VNFs are placed. If a VNF is not placed, or if 
  the vnf-host-cost tuple is not found, we assume that it does not 
  contribute anything to the overall cost.
  """
  
  cost = 0
  for v in solution["vnfs"]:
    vname = v["vnf_name"]
    if "place_at" in v and v["place_at"]:
      hname = v["place_at"][0]
      for c in solution["costs"]:
        if c["host"] == hname and c["vnf"] == vname:
          cost += c["cost"]
            
  return cost

def to_chromosome(solution):
  """Create an simple/lighter internal representation of a solution to be used by the GA operations.
  """
  
  genes = {}
  host_failure_rates = {}
  for h in solution["hosts"]:
    genes[h["host_name"]] = []
    if "failure_rate" in h:
      host_failure_rates[h["host_name"]] = h["failure_rate"]
    else:
      host_failure_rates[h["host_name"]] = 0.0
    
  for v in solution["vnfs"]:
    if "place_at" in v and v["place_at"] is not None:
      for p in v["place_at"]: # v[.] is a list, although it normally has just 1 element
        if "failure_rate" in v:
          vfrate =  v["failure_rate"]
        else:
          vfrate = 0.0
        genes[p].append({"vnf_name": v["vnf_name"], "failure_rate": vfrate})

  G = []
  for hname,vnfs in genes.iteritems():
    G.append(Gene(hname, vnfs, host_failure_rate = host_failure_rates[hname]))
  return Chromosome(G)

def from_chromosome(solution, C):
  """Update a solution object with placement information from chromosome C.
  
  What this function does is take the placement C and update the "place_at" fields of
  the solution. The solution is assumed to already have all information on hosts,
  vnfs, edges, costs, etc.
  """
  
  # First "clean" place_at fields, just in case
  for v in solution["vnfs"]:
    v["place_at"] = []

  for g in C.genes:
    for v in g.vnfs:
      # find vnf and place 
      for V in solution["vnfs"]:
        if V["vnf_name"] == v["vnf_name"]:
          #V["place_at"].append(hname)
          V["place_at"].append(g.hostname)
  return solution

def get_solution_global_latency(solution, processing_delay=False):
  """Get the average solution delay across all service.
  """
  n = 0
  latency = 0
  for s in solution["services"]:
    latency += get_solution_delay(solution, s["service_name"], processing_delay)
    n += 1
  return latency / n
  
def get_solution_availability(solution):
  """Calculate the availability of a placement.
  
  Service availability is defined as the probability that all service components
  are up and reachable. This breaks down to the following:
  - All VNFs are accessible, i.e., the VNFs themselves and the host they are placed at
  are up.
  - All host links are up.
  
  Each VNF, host, and host edge come with known failure rates. VNF-level, host-level and 
  link failures happen independently. However, the failure of a VNF can be either due
  to the VNF or the machine/DC that is hosting it. Therefore, the failures of VNFs
  which are placed at the same host are correlated. We define a "correlated group" as
  the set of VNFs placed at a specific host. A gene corresponds to a correlated group.
  The availability of the j-th gene (host) is given by a_j = (1-q_j)*Prod{1-q_v}. The
  product is over all VNFs v placed at host j. q_j is the failure rate of host j and 
  q_v is the failure rate of VNF v.
  
  The overall availability of a placement X is given by:
  A(X) = Pr{all correlated groups are up AND all host links are up} = 
       = Prod{a_j} * Prod{1 - q_l}.
  The second product term is over all the host links involved in the deployment.
  
  Note that we do not consider issues such as redundant links, etc. We assume that
  host links are virtual, so maybe there is redundancy implemented at the physical link
  level, but this is abstracted and is taken into account in the failure rate of each
  host link, as exposed by the "provider".
  """
  
  C = to_chromosome(solution)
  
  # Calculate group availabilities
  host_availability = 1.0
  for g in C.genes:
    gene_availability = 1.0
    for v in g.vnfs:
      if "failure_rate" not in v:
        f_rate = 0 # ignored (probably not included in json file)
      else:
        f_rate = v["failure_rate"]
      gene_availability *= (1.0 - f_rate)
    gene_availability *= (1.0 - g.host_failure_rate)
    
    host_availability *= gene_availability
    
  # for each VNF edge involved, find the corresponding host edge and calculate its reliability
  network_availability = 1.0
  for vedge in solution["vnf_edges"]:
    # get corresponding host edge
    hedge = get_host_edge(solution, vedge)
    if hedge:
      if "failure_rate" not in hedge:
        link_frate = 0.0 # if this information does not exist in json file
      else:
        link_frate = hedge["failure_rate"]
      link_failure_rate = link_frate
    else:
      (s,d) = get_mapped_vedge_endpoints(solution, vedge)
      if s == d:
        # If two VNFs are placed on the same host, the link is considered 100% reliable
        link_failure_rate = 0.0
      else:
        # We search for a shortest path between the two hosts ignoring link
        # capacities. There should always be a path, otherwise this would have 
        # been detected in previous checks (e.g., capacity)
        link_failure_rate = 0.0
        if s is not None and d is not None:
          # if one of the two is None, there's no actual link between the two
          # VNFs, so also no probability to fail.
          path = get_shortest_path(solution, s, d)
          if path:
            path_availability = 1.0
            for e in path:
              if "failure_rate" not in e:
                frate = 0.0
              else:
                frate = e["failure_rate"]
              path_availability *= (1 - frate)
              # account also for failures of intermediate nodes
              if e["source"] != s:
                # source and destination failure rates are already taken into account
                intermediate_host = filter(lambda x: x.get("host_name") == e["source"], solution["hosts"])[0]
                if "failure_rate" not in intermediate_host:
                  hfrate = 0.0
                else:
                  hfrate = intermediate_host["failure_rate"]
                path_availability *= (1 - hfrate)
            link_failure_rate = 1 - path_availability
    network_availability *= (1.0 - link_failure_rate)
    
  return host_availability * network_availability


def get_gene_availability(gene):
  """Returns an availability-based efficiency value for a gene.
  
  A gene's availability efficiency is calculated as the
  probability that the corresponding host and the VNFs on it do not fail.
  """
  gene_availability = 1.0
  for v in gene.vnfs:
    gene_availability *= (1.0 - v["failure_rate"])
  gene_availability *= (1.0 - gene.host_failure_rate)
  
  return gene_availability


def get_gene_latency(scenario, gene):
  """Returns a latency-based efficiency value for a gene.
  
  Since a gene's "latency" depends also on the placement of VNFs that
  are put on different hosts, thus belonging to other genes, it 
  cannot be calculated before a solution has been derived. However,
  since a latency efficiency metric is necessary at crossover time,
  we define it as follows:
  - For each VNFFG edge between a VNF of the gene towards a VNF 
  not placed at the gene, add the average latency of the host's outgoing edges
  - For each VNFFG edge between a VNF of another gene towards a VNF
  place at this gene's host, add the average latency of the host's incoming edges 
  Each value added in the sum is multiplied by the traversal probability.

  This function "promotes" genes with many VNFs (since self-edges are zero-latency)
  and/or genes of "fast" hosts (i.e., who have low-latency incoming and outgoing links)
    
  We ignore processing times, since they only depend on the VNFs and not
  their placement.
  """
  
  sum_lat = 0
  n_services = len(scenario["services"])
  service_latencies = []
  for service in scenario["services"]:
    traversed_vnfs = service["traversed_vnfs"]
    
    # get host's average incoming and outgoing latency
    out_latency = 0.0
    in_latency = 0.0
    n_out = 0
    n_in = 0  
    for hedge in scenario["host_edges"]:
      if hedge["source"] == gene.hostname:
        out_latency += hedge["delay"]
        n_out += 1
      if hedge["target"] == gene.hostname:
        in_latency += hedge["delay"]
        n_in += 1

    # For full mesh graphs, this /0 check is not necessary
    if n_out:
      out_latency /= n_out
    else:
      out_latency = 10000 # inf or 0?: no outgoing edge
    if n_in:
      in_latency /= n_in
    else:
      in_latency = 10000 # inf or 0?: no incoming edge
    
    # For each VNFFG edge v1->v2, check the "traversed_vnf" value for the
    # edge destination and use this as P(v2|v1)
    gene_latency = 0.0
    for vnf in gene.vnfs:
      # (not so efficient...)
      for vedge in scenario["vnf_edges"]:
        # if the VNF appears in a VNFFG edge either as source or destination,
        # get the probability that this edge is traversed, get the avg outgoing delay
        # and add their product to the overall gene latency.
        if vnf["vnf_name"] == vedge["source"]:
          hedge = get_host_edge(scenario, vedge)
          if hedge:
            hlat = out_latency
          else:
            # If two VNFs are placed on the same host, there's no delay
            hlat = 0
          if vedge["target"] in traversed_vnfs:
            probability = traversed_vnfs[vedge["target"]]
          else:
            probability = 0.0
          gene_latency += probability*hlat
        # something similar for incoming edges
        if vnf["vnf_name"] == vedge["target"]:
          hedge = get_host_edge(scenario, vedge)
          if hedge:
            hlat = in_latency
          else:
            # same as before
            hlat = 0
          if vedge["source"] in traversed_vnfs:
            probability = traversed_vnfs[vedge["source"]]
          else:
            probability = 0.0
          gene_latency += probability*hlat
    sum_lat += gene_latency
    service_latencies.append(gene_latency)
    
  return sum_lat / n_services
  # uncomment to return the min latency across services instead of the avg
  #return min(service_latencies)
  

def check_reachability(solution):
  """Check if for each VNF edge there exists a host link or the VNFs involved are placed at the same host
  """
  
  for vedge in solution["vnf_edges"]:
    v1 = filter(lambda x: x.get("vnf_name") == vedge["source"], solution["vnfs"])[0]
    v2 = filter(lambda x: x.get("vnf_name") == vedge["target"], solution["vnfs"])[0]
    
    if v1 is None or v2 is None:
      # In this case, reachability does not matter
      continue

    # find source host
    if v1["place_at"][0] == v2["place_at"][0]:
      # this VNF edge is ok, both endpoints are on the same host
      continue
    
    # Otherwise, we need to see if there's a host edge. If not, placement is illegal
    if not get_host_edge(solution, vedge):
      return False
  return True

######################
## Some diagnostics ##
######################
def get_used_hosts(solution):
  hused = []
  for v in solution["vnfs"]:
    if v["place_at"][0] not in hused:
      hused.append(v["place_at"][0])
  return hused

def get_used_host_links(solution):
  hedges = []
  for ve in solution["vnf_edges"]:
    he = get_host_edge(solution, ve)
    path_edges = []

    if he is None:
      # maybe placed at the same host
      v1 = filter(lambda x: x.get("vnf_name") == ve["source"], solution["vnfs"])
      if v1:
        # same hack
        v1 = v1[0]
      v2 = filter(lambda x: x.get("vnf_name") == ve["target"], solution["vnfs"])
      if v2:
        v2 = v2[0]

      # find source host
      if not v1 or not v2:
        # One of the two VNF links has a null endpoint.
        # In this case, no problem...(special case where dst is "None" -- to re-check)
        continue
      if v1["place_at"][0] == v2["place_at"][0]:
        path_edges = [{"capacity": 100000, "delay": 0, "source": v1["place_at"][0], "target": v1["place_at"][0]}]
      else:
        # There is no direct edge between the two hosts.
        # In this case, find a (shortest) path between the hosts and add to 
        # used host links all the edges of the path
        logging.warn("Null edge:" + v1["place_at"][0] + "->" + v2["place_at"][0])
        path = get_shortest_path(solution, v1["place_at"][0], v2["place_at"][0])
        for e in path:
          path_edges.append(e)
    else:
      path_edges = [he]
    for pe in path_edges:
      if pe not in hedges:
        hedges.append(pe)
      
  return hedges

def add_missing_links(scenario):
  """Add necessary edges to the host graph so that it becomes a full mesh.
  
  For each host link, add a symmetric link in the opposite direction. This is
  necessary if the scenario file assumes undirected links. Also, since the 
  algorithm operates on a full mesh, if there is no direct link between two 
  hosts, we complement the graph with such a link, whose latency is the sum of 
  the latencies of all the substrate links.  
  """
  
  new_edges = []
  
  for h in scenario["host_edges"]:
    rev = find_reverse_edge(scenario, h)
    # check if the reverse edge already exists somehow in the scenario
    if rev is not None:
      continue
    new_edge = {
      "capacity": h["capacity"], 
      "delay": h["delay"], 
      "source": h["target"],
      "target": h["source"]
    }
    if "id" in h:
      new_edge.update({"id": str(h["id"]) + "-inv"})
    new_edges.append(new_edge)

  for e in new_edges:
    scenario["host_edges"].append(e)


def add_vnf_edge_mapping(solution):
  """Add the host edge to which each VNF edge is mapped.
  """

  for ve in solution["vnf_edges"]:
    he = get_host_edge(solution, ve)
    if he is None:
      v1 = filter(lambda x: x.get("vnf_name") == ve["source"], solution["vnfs"])
      if v1:
        v1 = v1[0]
      v2 = filter(lambda x: x.get("vnf_name") == ve["target"], solution["vnfs"])
      if v2:
        v2 = v2[0]

      if not v1 or not v2:
        # One of the two endpoints is "None"
        # Nothing to map (special case for VNFlink dst being None (to recheck)
        continue

      # find source host
      if v1["place_at"][0] == v2["place_at"][0]:
        source = v1["place_at"][0]
        target = v1["place_at"][0]
        lat = 0
        ve["host_edge"] = {"source": source, "target": target, "delay": lat}
        # this host_edge has no ID since it's intra-host
      else:
        logging.warn("Null edge:" + v1["place_at"][0] + "->" + v2["place_at"][0])
    else:
      source = he["source"]
      target = he["target"]
      lat = he["delay"]
      ve["host_edge"] = {"source": source, "target": target, "delay": lat}
      if "id" in he:
        ve["host_edge"].update({"id": he["id"]})

#################################################################
# The following functions are related with cases where
# more than one links are possible between the same pair of hosts
# For the moment, they are unused
#################################################################

def update_superedge(hedge, superedges):
  """Create or update a "superedge"
  """
  for se in superedges:
    if se["source"] == hedge["source"] and se["target"] == hedge["target"]:
      se["capacity"] += hedge["capacity"]
      se["utilization"] += hedge["utilization"]
      return
  # otherwise, add new superedge
  superedges.append({
    "source": hedge["source"],
    "target": hedge["target"],
    "capacity": hedge["capacity"],
    "utilization": hedge["utilization"]
  })

def get_superedge(hedge, solution):
  for se in superedges:
    if se["source"] == hedge["source"] and se["target"] == se["target"]:
      return se
  return None

def get_inverse_superedge(hedge, superedges):
  for se in superedges:
    if se["source"] == hedge["target"] and se["target"] == se["source"]:
      return se
  return None

def check_link_capacity_constraints_multi(solution):
  """Check if a potential solution violates the link capacity constraints,
  considering a host graph where it is possible to have multiple
  host links between the same pair of hosts.

  """
  for hedge in solution["host_edges"]:
    hedge["utilization"] = 0

  # superedge: an edge that groups all host edges between the same pair of hosts
  superedges = []
  # create superedges
  for hedge in solution["host_edges"]:
    update_superedge(hedge, superedges) 

  # for each vedge, get corresponding superedge and update utilization
  # (again, we mirror edge util. to the inverse edge)
  for vedge in solution["vnf_edges"]:
    # get the src-dst hosts for this edge (get_host_edge will return one of the possible host edges)
    # to retrieve the corresponding superedge
    hedge = get_host_edge(solution, vedge)
    if hedge:
      se = get_superedge(hedge, superedges)
      se["utilization"] += vedge["traffic"]
      se_rev = get_inverse_superedge(hedge, superedges)
      se_rev["utilization"] += vedge["traffic"]
      if se["utilization"] > se["capacity"] or se_rev["utilization"] > se_rev["capacity"]:
        return False
  return True
#################################################################

#################################################################
# Djikstra's algorithm
#################################################################
def _get_host_neighbors(scenario, h, flowsize = 0):
  retval = []
  for he in scenario["host_edges"]:
    if he["source"] == h["host_name"] and (flowsize == 0 or flowsize + he["utilization"] < he["capacity"]):
      retval.append(he["target"])
  return retval

def _get_host_edge_info(scenario, src, dst):
  for he in scenario["host_edges"]:
    if he["source"] == src and he["target"] == dst:
      return he
  return None

def _extract_min(Q):
  minval = 100000000
  i = 0
  idx = -1
  for q in Q:
    if q["dist"] < minval:
      minval = q["dist"]
      idx = i
    i = i + 1
  return Q.pop(idx)

def _djikstra(scenario, s, flowsize = 0):
  src = filter(lambda x: x.get("host_name") == s, scenario["hosts"])[0]
  for h in scenario["hosts"]:
    h["dist"] = 1000000
    h["pred"] = None
  src["dist"] = 0

  # put all nodes in the set
  Q = []
  for h in scenario["hosts"]:
    Q.append(h)

  while len(Q) > 0:
    u = _extract_min(Q)

    # get u's neighborhood (adj has host names, not full host elements) 
    adj = _get_host_neighbors(scenario, u)
    #print u["host_name"] + " has neighbors: " + str(adj)
    for a in adj:
      # get full neighbor host info
      v = filter(lambda x: x.get("host_name") == a, scenario["hosts"])[0]
      # get edge latency
      he = _get_host_edge_info(scenario, u["host_name"], a)
      if v["dist"] > u["dist"] + he["delay"]:
        v["dist"] = u["dist"] + he["delay"]
        v["pred"] = u["host_name"]

def get_shortest_path(scenario, s, d, flowsize = 0):
  """Run shortest path algorithm and return the set of host edges that compose
  the shortest path from src to dst. Flowsize is the amount of traffic that
  each edge of the path should be able to accommodate.
  """
  _djikstra(scenario, s, flowsize)
  path = []
  src = filter(lambda x: x.get("host_name") == s, scenario["hosts"])[0]
  dst = filter(lambda x: x.get("host_name") == d, scenario["hosts"])[0]
  pred = dst["pred"]
  cur = dst
  while pred:
    he = _get_host_edge_info(scenario, pred, cur["host_name"])
    path.append(he)
    cur = filter(lambda x: x.get("host_name") == pred, scenario["hosts"])[0]
    pred = cur["pred"]
  return path

