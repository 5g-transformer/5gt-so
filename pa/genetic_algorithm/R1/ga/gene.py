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
Class representing a gene. A chromosome represents a part of a 
solution, and, in particular, a host and the group of VNFs placed
on it.

- hostname: Name of the host (as in the scenario file)
- vnfs: A list of strings, each corresponding to the name of a VNF
- efficiency: A measure of the gene's "quality". This depends on the
case and the optimization objectives. E.g., in this case, we use
a gene's cost (sum of costs of VNFs when placed at the specific host).
The efficiency is used to rank genes during the crossover operation.
- host_failure_rate: Probability that the corresponding host fails.
#################################################################
"""

class Gene(object):
  """Class representing a gene. The effficiency of a gene is the cost of
  the group of VMs placed at the respective host.
  """
  
  def __init__(self, hostname, vnfs, efficiency = None, host_failure_rate = 0.0):
    self.hostname = hostname
    self.vnfs = vnfs
    self.efficiency = efficiency
    self.host_failure_rate = host_failure_rate
      
  def __str__(self):
    return str({"host": self.hostname, "failure_rate": self.host_failure_rate, "vnfs": self.vnfs, "efficiency": self.efficiency})

  def __repr__(self):
    return str({"host": self.hostname, "failure_rate": self.host_failure_rate, "vnfs": self.vnfs, "efficiency": self.efficiency})

