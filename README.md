# 5gt-so
Service Orchestrator



| Release 2 Features |
| --- |
| Extended REST-based NBI offering catalogue and lifecycle management functions:
- NFV-NS scaling
- NFV-NS lifecycle management (ID creation, instantiation, operation status, NS info, termination)
- n-boarding, removal, queries of descriptors/packages stored in catalogues
 |
| Extended Service Orchestration supporting:
- management functions (on-boarding) for descriptors and packages of NFV-NS, Virtual Network Function (VNF), AppD stored in catalogues
- NFV-NS scaling and extended NFV-NS lifecycle management
- NFV-NS composition and federation
- service assurance through NFV-NS auto-scaling leveraging SLA manager
- automatic translation of NSDs, VNFDs to MANO formato
 |
| Extended Resource Orchestration functions:
- placement decisions based on vertical service requirements and abstracted infrastructure information provided by 5GT-MTP, including single Point of Presence (PoP) deployments and multi-PoP deployments through Wide Area Network (WAN)
- triggering and coordination of resource allocation and release operations triggered by NFV-NS instantiation, termination, auto-scaling
- interworking with multiple orchestration platforms (OSM and Cloudify)
- composite NFV-NS resource management (for service composition and federation)
 |
| 3 Placement Algorithm (PA) engines supported:
- vertical service requirements addressed also in terms of location or MEC constraints
- decisions made based on underlying MTP infrastructure information that is dynamically retrieved .
 |
| Extended Cloudify Wrapper to provide automation in NFV-NS operations while involving the Cloudify orchestrator for all the 5GT-SO workflows |
| Extended OSM Wrapper to provide automation in NFV-NS operations while involving the OSM orchestrator for all the 5GT-SO workflows |
| Fully integrated monitoring platform supporting lifecycle management through configuration of monitoring jobs and service assurance operations through the Service Level Agreement (SLA) manager (see Table 2). |
| Extended Resource Orchestration Execution Entity acting as client to 5GT-MTP also for resource status retrieval operations:
- collection of resource topological and capacity information
-  requests for allocation and release of networking (also for inter-domain communication) and computing resource operations
  |
| Integration with the final 5GT-MTP features:
- allocation/release of computing and networking resources in both cloud and WAN
- allocation/release of intra- and inter-domain resources advertisement of resource information (e.g., capacity, topology)
 |
| Integration with the final 5GT-VS, supporting the full set of NBI REST API operations for:
- NFV-NS lifecycle management
- n-boarding, removal, updates, queries and enabling/disabling of descriptors and packages stored in catalogues
 |
| SLA Manager and Monitoring Manager, supporting service assurance and auto-scaling operations on NFV-NSs leveraging the Monitoring Platform |
| Service composition and federation support for deployment of NFV-NSs in one or multiple domains (involving different 5GT-SOs) |


