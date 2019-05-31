# A Genetic Algorithm for VNF placement

## Description
Implementation of a Genetic Algorithm for VNF placement. Depending on its 
configuration, it can optimize for (i) cost, (ii) latency, or (iii) service
availability, taking into account the respective constraints.

## Software releases
- `R1`: First release of the GA implementation. Supports the first version of 
the common 5GT-SO placement algorithm API.
- `R2`: Second release of the GA implementation. Supports the second version of 
the common 5GT-SO placement algorithm API, including location constraints, MEC
requirements and infrastructure capabilities, as well as various other
improvements, such as more initial feasibility checks and more generic NFVI
topologies.

Please refer to the individual README files for more details and instructions to
set up and run the algorithm.
