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
A genetic algorithm for VM placement.

The relevant parameters can be tuned in the configuration file.
The scenario_file parameter must point to a valid JSON-formatted
file with all the scenario parameters.
#################################################################
"""

from random import *
from operator import itemgetter, attrgetter
import sys
import time 
import string
import math
import json 
import os
import copy
import logging
import random
from datetime import datetime

from chromosome import Chromosome
from gene import Gene
import helpers

class GA(object):
  """Genetic Algorithm class.
  """
  
  ERR_MALFORMED_INPUT = 400
  ERR_NO_INPUT_PROVIDED = 410
  ERR_NO_FEASIBLE_SOLUTION = 420

  def __init__(self, configuration):
    """Constructor function.
    """
    
    # seed random number generator (if this option is set in the config file)
    if "seed" in configuration:
      self.seed = configuration["seed"]
    else:
      self.seed = int(time.time())
    random.seed(self.seed)
    
    # Load GA-specific params (S, G, Rc, Rm)
    # Load VNFFG, host graph, constraints, etc.
    self.solution_pool_size = configuration['solution_pool_size']
    self.generations = configuration['generations']
    self.crossover_rate = configuration['crossover_rate']
    self.mutation_rate = configuration['mutation_rate']
    self.convergence_check = configuration['convergence_check']
    self.error = None
    self.error_string = None

    if self.convergence_check:
      self.delta = configuration['delta']
      self.stop_after = configuration['stop_after']

    if "generations_file" in configuration:
      self.generations_file = configuration['generations_file']
    else:
      self.generations_file = None

    optimize_for = configuration['optimize_for'].lower()
    if optimize_for in ["cost", "availability", "latency"]:
      self.optimize_for = optimize_for
    else:
      # default criterion
      self.optimize_for = "cost"
    
    self.processing_latency = configuration["processing_latency"]
    
    loglevel = getattr(logging, configuration["loglevel"].upper(), None)
    logging.basicConfig(level=loglevel)
    
    if 'scenario' in configuration:
      self.scenario = configuration["scenario"]
      if "scenario_file" not in configuration:
        self.scenario_file = None
    elif 'scenario_file' in configuration:
      self.scenario_file = configuration["scenario_file"]
      try:
        with open(configuration['scenario_file']) as fp:
          self.scenario = json.load(fp)
      except:
        logging.error("Error loading scenario file. Possibly malformed...")
        self.error_string = "Error loading scenario file. Possibly malformed."
        self.error = GA.ERR_MALFORMED_INPUT
    else:
      logging.error("Scenario not provided.")
      self.error_string = "No input provided."
      self.error = GA.ERR_NO_INPUT_PROVIDED
    
    if configuration["loglevel"].upper() != "NONE":
      self.print_configuration()

    if not helpers.check_global_feasibility(self.scenario):
      logging.warn("No feasible solution exists")
      self.error_string = "Initial feasibility check failed."
      self.error = GA.ERR_NO_FEASIBLE_SOLUTION
    
  def print_configuration(self):
    """Print the configuration
    """
    
    print "Configuration:\n-------------------------------"
    print "- Optimization criterion:\t" + str(self.optimize_for)
    print "- Consider proc. latency:\t" + str(self.processing_latency)
    print "- Solution pool size:\t\t" + str(self.solution_pool_size)
    print "- Number of generations:\t" + str(self.generations)
    print "- Crossover rate:\t\t" + str(self.crossover_rate)    
    print "- Mutation rate:\t\t" + str(self.mutation_rate)
    print "- Scenario file:\t\t" + str(self.scenario_file)
    print "- Log data per generation:\t" + str(self.generations_file)
    print "- Enable convergence check:\t" + str(self.convergence_check)
    if self.convergence_check:
      print "\t+ Delta:\t\t" + str(self.delta)
      print "\t+ Stop after:\t\t" + str(self.stop_after)
    print "- RNG seed:\t\t\t" + str(self.seed)
    print "-------------------------------\n"


  def gene_efficiency(self, gene):
    """Gene efficiency function
    
    A gene corresponds to the VNFs placed on a single host.
    Various options exist to measure its efficiency. If we take a cost-driven
    perspective, we can define a gene's efficiency as the sum of costs of
    the VNFs placed on the specific host. For a latency driven version, we
    can use an estimate of the sum of latencies of all incindent edges to the VNFs
    placed on the host. An availability centric function would measure the
    probability that none of the VNFs placed on the host fail. See the comments
    on helpers.py for details.
    
    Depending on the optimization criterion selected in the algorithm configuration,
    one of the three efficiency functions is used.
    """
    
    hname = gene.hostname
    vnfs = gene.vnfs
    
    if self.optimize_for == "cost":
      # calculate cost of the VNFs assigned to the specific host
      cost = 0
      # [maybe a bit inefficient]
      for v in vnfs:
        for c in self.scenario["costs"]:
          if c["vnf"] == v["vnf_name"] and c["host"] == hname:
            cost += c["cost"]     
      gene.efficiency = cost
    elif self.optimize_for == "availability":
      gene.efficiency = helpers.get_gene_availability(gene)
    elif self.optimize_for == "latency":
      gene.efficiency = helpers.get_gene_latency(self.scenario, gene)      
    return gene.efficiency


  def fitness(self, C):
    """Calculate the fitness of chromosome C.
    
    The fitness of a solution is its cost. First convert C to the full representation.
    Then calculate its cost. (The lower the better). 
    """
    
    solution = copy.deepcopy(self.scenario)
    helpers.from_chromosome(solution, C)
    if self.optimize_for == "availability":
      return helpers.get_solution_availability(solution)
    elif self.optimize_for == "latency":
      return helpers.get_solution_global_latency(solution, self.processing_latency)    
    else: #cost
      return helpers.get_solution_cost(solution)
    

  def init_solution_pool(self):
    """Initialize solution pool.
    
    Generate S feasible solutions/placements as follows: For each VNF, 
    select a random host. If it has enough capacity, place VNF there.
    Otherwise look for another host.
    """
    self.solution_pool = []
    solutions_to_generate = self.solution_pool_size

        
    while solutions_to_generate > 0:
      # TODO: Remove the deepcopy, just clear "place_at" fields
      solution = copy.deepcopy(self.scenario)
      
      reset = False
      for v in solution['vnfs']:
        if reset is True:
          # Solution infeasible. Try another one...
          logging.debug("Infeasible solution. Resetting")
          break

        vnf_placed = False
        while not vnf_placed:
          if not helpers.check_if_there_is_space(solution, v):
            # reset solution and start from scratch
            reset = True
            break

          h = choice(solution["hosts"])            
          v["place_at"] = [h["host_name"]]

          # First check if it is allowed to place v at h
          # If not, try another one
          if not helpers.check_if_placement_allowed(solution, h["host_name"], v["vnf_name"]):
            logging.debug("init_solution_pool: Not allowed, trying another host")
            v["place_at"] = None
            continue          
          
          # check if h has the available resources to host v
          # If capacity will be exceeded, try another host
          if helpers.check_host_capacity_constraint(solution, h):
            vnf_placed = True
            logging.debug("init_solution_pool: VNF " + v["vnf_name"] + " placed at " + h["host_name"])
          else:
            v["place_at"] = None        

      # check if the solution violates any MEC constraints
      mec_constraints_ok = helpers.check_mec_constraints(solution)
      if not mec_constraints_ok:
        logging.debug("init_solution_pool: Mec constraint violated")
        continue
      # check if we're violating location constraints
      location_constraints_ok = helpers.check_location_constraints(solution)
      if not location_constraints_ok:
        logging.debug("init_solution_pool: Location constraint violated")
        continue
      # Check if the solution violates any link capacities
      link_constraints_ok = helpers.check_link_capacity_constraints(solution)
      if not link_constraints_ok:
        logging.debug("init_solution_pool: Link capacity constraint violated")
        continue
      delay_constraints_ok = helpers.check_delay_constraints(solution)
      if not delay_constraints_ok:
        logging.debug("init_solution_pool: Delay constraint violated")
        continue
      #reachability_ok = helpers.check_reachability(solution)
      #if not reachability_ok:
      #  continue
      if reset is False:
        logging.debug(helpers.show_host_link_status(solution))
        logging.debug("Solution cost: " + str(helpers.get_solution_cost(solution)) + ", availability: " + str(helpers.get_solution_availability(solution)) + ", latency: " + str(helpers.get_solution_global_latency(solution)))
        # Store the simplified "chromosome" representation of the solution
        C = helpers.to_chromosome(solution)
        self.solution_pool.append(C)
        solutions_to_generate -= 1

  def crossover(self):
    """Crossover operation.
    
    - Select two random chromosomes
    - Rank their genes according to an efficiency function
    - Create a new chromosome by taking the "best" genes until all VNFs are placed
    (if when adding a gene one of its VNFs is already placed, just ignore it)
    """

    # Pick two random chromosomes (C1 and C2 could coincide)    
    C1 = choice(self.solution_pool)
    C2 = choice(self.solution_pool)
    
    # Create a list of all their genes (i.e., hosts with the VNFs assigned to them)
    genes = copy.deepcopy(C1.genes + C2.genes)

    # sort genes by efficiency (lowest cost first)
    for g in genes:
      g.efficiency = self.gene_efficiency(g)
      
    # For availability, sort in descending order (as we want the max here)
    rev = False
    if self.optimize_for == "availability":
      rev = True
    genes = sorted(genes, key=attrgetter('efficiency'), reverse = rev)
    
    # vnfs to place (list of strings)
    vnfs = [v["vnf_name"] for v in self.scenario["vnfs"]]
    
    # create new chromosome
    new_genes = []
    # continue as long as there are still vnfs to place
    while vnfs and genes:
      # if the gene host has already been put in the chromosome,
      # skip the gene. This ensures that at this step no capacity 
      # constraints will be violated.
      if genes[0].hostname in [g.hostname for g in new_genes]:
        del(genes[0])
      else:
        # if a VNF of the gene is not in the remaining vnf list, remove it from the gene
        # since this means it's already placed
        for v in genes[0].vnfs:
          if v["vnf_name"] not in vnfs:
            genes[0].vnfs.remove(v)

        # finally, add the new gene
        # also, remove its vnfs from the list of pending ones (there should be a more efficient way to do this)
        new_genes.append(Gene(genes[0].hostname, genes[0].vnfs, host_failure_rate = genes[0].host_failure_rate))
        for v in genes[0].vnfs:
          if v["vnf_name"] in vnfs:
            vnfs.remove(v["vnf_name"])
        del(genes[0])
      
    C = Chromosome(new_genes)
    
    # Now we need to check if there are any VNFs left unassigned
    # If so, we place them anywhere they fit and are allowed to
    solution = copy.deepcopy(self.scenario)
    helpers.from_chromosome(solution, C)
    while vnfs:
      vname = vnfs.pop()
      v = filter(lambda x: x.get("vnf_name") == vname, solution["vnfs"])[0]
      host = helpers.check_if_there_is_space(solution, v)
      if host: # host found, place VNF
        v["place_at"].append(host["host_name"])
      else:
        # Normally we should not arrive here, but, if so,
        # this means that there's nowhere to place the VNF
        # in this case, we return None and the caller will see what to do
        return None
    
    # perform constraint checks
    mec_constraints_ok = helpers.check_mec_constraints(solution)
    location_constraints_ok = helpers.check_location_constraints(solution)
    link_constraints_ok = helpers.check_link_capacity_constraints(solution)
    delay_constraints_ok = helpers.check_delay_constraints(solution)

    if link_constraints_ok and delay_constraints_ok and mec_constraints_ok and location_constraints_ok:
      # return the chromosome 
      return helpers.to_chromosome(solution)
    else:
      return None

  def mutation(self):
    """Mutation operator.
    
    For each chromosome in the solution pool, decide according to the mutation
    rate if we'll modify it or not. If its selected for mutation, we create a 
    mutant as follows: We select two random hosts and swap two random VNFs. If 
    none of the selected hosts has VNFs on it, we select two other hosts and so on.
    If the constraints are violated, the mutant is rejected.
    """

    counter = 0
    for s in self.solution_pool:
      if uniform(0, 1) <= self.mutation_rate:
        logging.debug("Mutating solution: " + str(s))
        # create a copy of the chromosome
        scopy = copy.deepcopy(s)

        # Corner-case: There's just one gene in the chromosomes, so nothing to
        # mutate
        if len(scopy.genes) < 2:
          continue
        
        # pick two hosts
        while True:
          h1 = choice(scopy.genes)
          h2 = choice(scopy.genes)
          if h1 == h2:
            continue
          if h1.vnfs or h2.vnfs:
            break
                    
        # pick one VNF from each host
        v1 = None
        v2 = None
        if h1.vnfs:
          v1 = choice(h1.vnfs)
          h1.vnfs = [x for x in h1.vnfs if x["vnf_name"] != v1["vnf_name"]]
        if h2.vnfs:
          v2 = choice(h2.vnfs)
          h2.vnfs = [x for x in h2.vnfs if x["vnf_name"] != v2["vnf_name"]]
        
        # swap the two VNFs
        if v2:
          h1.vnfs.append(v2)
        if v1:
          h2.vnfs.append(v1)
        
        # create a solution represented in the full format
        S = helpers.from_chromosome(self.scenario, scopy)
        reject = False
        
        # check constraints
        for v in S["vnfs"]:
          hname = v["place_at"][0]
          vname = v["vnf_name"]
          if not helpers.check_if_placement_allowed(S, hname, vname):
            # There's a VNF "illegally" placed
            reject = True
            break
        
        if not reject:
          if helpers.check_mec_constraints(S) is False:
            reject = True
        if not reject:
          if helpers.check_location_constraints(S) is False:
            reject = True
        if not reject:   
          for h in S["hosts"]:
            if helpers.check_host_capacity_constraint(S, h) is False:
              reject = True
              break
        if not reject:
          if helpers.check_link_capacity_constraints(S) is False:
            reject = True
        if not reject:
          if helpers.check_delay_constraints(S) is False:
            reject = True
            
        mutant = helpers.to_chromosome(S)
        
        if not reject:
          # all constraints ok
          # delete old solution and replace with mutant
          self.solution_pool[counter] = mutant          
          logging.debug("Mutant ACCEPTED")
        else:
          logging.debug("Mutant REJECTED")
          pass
        counter += 1
       
  def generation(self):
    """A GA generation to produce a new solution pool.
    
    This executes crossover and mutation operations to produce
    offspring and keeps the top-ranking solutions according to the
    fitness function.
    
    It also returns the fitness function of the best solution
    """ 
    # select number of offspring
    nOffspring = int(self.crossover_rate * self.solution_pool_size)
    
    # for each offspring
    while nOffspring > 0:
      # generate a new chromosome from crossover
      C = self.crossover()
      
      # if C is none, this means that for some reason
      # the chromosome violated some constraint
      if C:
        # Valid offspring is returned 
        nOffspring -= 1
        # add it to the solution pool
        self.solution_pool.append(C)

    # mutation
    self.mutation()
        
    # select top-S chromosomes according to their fitness value 
    # and create new solution pool
    for s in self.solution_pool:
      s.fitness = self.fitness(s)
    
    # if availability is the criterion, sort in descending order (maximization problem)
    # otherwise, the opposite.
    rev = False
    if self.optimize_for == "availability":
      rev = True
    self.solution_pool = sorted(self.solution_pool, key=attrgetter('fitness'), reverse = rev)[0:self.solution_pool_size]
    
    return self.solution_pool[0].fitness


  def execute(self):
    """Run the genetic algorithm.
    
    Returns the scenario JSON object with placement decisions plus some 
    algorithm-specific information.
    """

    # Fill in missing edges
    helpers.add_missing_links(self.scenario)
    
    # check if we will store data per generation in a file
    log_generation_data = False
    if self.generations_file is not None:
      try:
        gen_fp = open(self.generations_file, "w+")
        log_generation_data = True
        gen_fp.write("# Scenario: " + str(self.scenario_file) + "\n")
        gen_fp.write("# Seed: " + str(self.seed) + "\n")
        gen_fp.write("#-----------------------------------------------\n")
        gen_fp.write("# Generation\tFitness\t\tTimestamp\n")
      except:
        logging.warn("Error opening/writing at " + self.generations_file)
        pass
        
    prev_obj_value = 100000000 #inf   
    if self.convergence_check: 
      remaining_generations = self.stop_after
    
    start_time = datetime.now()
    
    self.init_solution_pool()
    for i in range(0, self.generations):
      obj_value = self.generation()
      # get a timestamp for this generation
      dt = datetime.now() - start_time
      # convert to seconds. dt.days should really not matter...
      time_taken = dt.days*24*3600 + dt.seconds + dt.microseconds/1000000.0

      logging.info("Generation/fitness (" + self.optimize_for + ")/timestamp: " + str(i) + "\t" + str(obj_value) + "\t" + str(time_taken))
      if log_generation_data:
        gen_fp.write(str(i) + "\t\t" + str(obj_value) + "\t" + str(time_taken) + "\n")
        
      # if we're checking for convergence to finish execution faster
      # we have to do some checks
      if self.convergence_check:
        if abs(obj_value - prev_obj_value) < self.delta:
          # the solution fitness did not significantly changed
          remaining_generations -= 1
        else:
          remaining_generations = self.stop_after
        
        # the algorithm converged
        if remaining_generations < 0:
          break
        prev_obj_value = obj_value
    final_solution = helpers.from_chromosome(self.scenario, self.solution_pool[0])

    # add extra information about solution performance (cost, availability, latency, time taken, # generations)
    # and indications about constraint violations
    info = self.get_solution_info(final_solution)
    info["generations"] = i + 1
    info["execution_time"] = time_taken
    info["link_capacity_constraints_ok"] = True
    info["delay_constraints_ok"] = True
    info["host_capacity_constraints_ok"] = True
    info["mec_constraints_ok"] = True
    info["legal_placement"] = True

    # some final checks
    if not helpers.check_mec_constraints(final_solution):
      logging.warn("Final solution violates MEC constraints")
      info["mec_constraints_ok"] = False
    if not helpers.check_location_constraints(final_solution):
      logging.warn("Final solution violates location constraints")
      info["location_constraints_ok"] = False
    if not helpers.check_link_capacity_constraints(final_solution):
      logging.warn("Final solution violates link capacity constraints")
      info["link_capacity_constraints_ok"] = False
    if not helpers.check_delay_constraints(final_solution):
      logging.warn("Final solution violates delay constraints")
      info["delay_constraints_ok"] = False
    for h in final_solution["hosts"]:
      if not helpers.check_host_capacity_constraint(final_solution, h):
        logging.warn("Final solution violates host " + h["host_name"] + " capacity constraints")
        info["host_capacity_constraints_ok"] = False
    for v in final_solution["vnfs"]:
      if not helpers.check_if_placement_allowed(final_solution, v["place_at"][0], v["vnf_name"]): 
        logging.warn("Final solution includes illegal placement of " + v["place_at"][0] + " at " + v["vnf_name"])
        info["legal_placement"] = False    
    final_solution["solution_performance"] = info

    used_hosts = helpers.get_used_hosts(final_solution)
    logging.info("Used hosts:")
    for uh in used_hosts:
      logging.info(uh)
    used_hedges = helpers.get_used_host_links(final_solution)
    logging.info("Used host edges:")
    for ue in used_hedges:
      logging.info(ue["source"] + " -> " + ue["target"] + " (" + str(ue["delay"]) + ")")

    # Add host edge mapping info to VNF edges  
    helpers.add_vnf_edge_mapping(final_solution)    
    return final_solution


  def get_solution_info(self, solution):
    """Get information about the cost, service availability and latency of a solution
    """
    latency_full = helpers.get_solution_global_latency(solution, True)
    latency_nwk = helpers.get_solution_global_latency(solution)
    return {"cost": helpers.get_solution_cost(solution), "availability": helpers.get_solution_availability(solution), "latency": {"processing": latency_full - latency_nwk, "network": latency_nwk, "total": latency_full}}

