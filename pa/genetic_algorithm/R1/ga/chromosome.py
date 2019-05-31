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
Class representing a chromosome. A chromosome represents a solution,
i.e., a specific placement.

genes: A list of Gene instances (each corresponding to a host and
the group of VNFs placed on it.
fitness: Value of the fitness function for this chromosome
#################################################################
"""

class Chromosome(object):
  """Class representing a chromosome, i.e., a set of genes, each representing
  the group of VNFs placed at a specific host.
  """
  
  def __init__(self, genes, fitness = None):
    self.genes = genes
    self.fitness = fitness

  def __str__(self):
    return str({"genes": self.genes, "fitness": self.fitness})

  def __repr__(self):
    return str({"genes": self.genes, "fitness": self.fitness})

