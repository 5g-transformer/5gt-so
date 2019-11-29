#!/usr/bin/env python
# coding: utf-8

# In[6]:


import json,sys,os
from os.path import expanduser as eu
from hac import GreedyAgglomerativeClusterer
import networkx as nx
from collections import defaultdict
from itertools import combinations


# # Clustering!
# In this notebook, we perform the actual clustering. Given an input scenario, we:
# 1. perform all possible clusterings, from 1 to $\min\{|\mathcal{V},|,|\mathcal{H}|\}$;
# 2. for each possible clustering, check if a _straightforward_ clustering, where bigger VNF clusters are associated with bigger host clusters, is _prima facie_ feasible.
# 
# The path of input and output files (both in JSON) are specified as environment variables.

# In[7]:


input_path=os.getenv('INPUT_PATH',eu('test/release2/test_req_sap_cp.json'))
output_path=os.getenv('OUTPUT_PATH',eu('test/release2/test_req_sap_cp_cluster_decisions.json'))


# Before creating a VNF graph, we treat those **SAPs associated to a VL** as a VNF with zero requirements

# In[15]:

def cluster(PARequest):
    """Executes the clustering of the PARequest

    :PARequest: REST API PARequest
    :returns: PARequest dictionary with the clustering decisions

    """

    scenario=PARequest
    i = 0
    vlSaps = [(s, sIdx) for (s, sIdx) in zip(scenario['nsd']['SAP'],\
                            range(len(scenario['nsd']['SAP'])))]\
                if 'SAP' in scenario['nsd'] else [] # Maybe no SAPs
    vlSaps = list(filter(lambda (s, sIdx): 'VNFLink' in s and s['VNFLink'] != '', vlSaps))
    
    for (sap, sapIdx) in vlSaps:
        # Find the associated VNFLink
        vnfLink = [vl for vl in scenario['nsd']['VNFLinks'] if vl['id'] == sap['VNFLink']][0]
        sapVNF = {
            'VNFid': 'sap_' + vnfLink['id'],
            'SAPidx': sapIdx,
            'instances': 1,
            'requirements': {'cpu': 0, 'ram': 0, 'storage': 0},
            'failure_rate': 0,
            'processing_latency': 0,
            'CP': [{
                'cpId': 'sap_' + vnfLink['id'],
                'VNFLink': vnfLink
            }]
        }
        scenario['nsd']['VNFs'].append(sapVNF)
        i += 1

    
    # Now, we build two graphs, one for VNFs and one for VNF. Weights are:
    # * for the VNF graph, the traffic between VNFs;
    # * for the host graph, the capacity of links.
    
    # In[60]:
    
    
    vnf_graph=nx.Graph()
    for vl in scenario['nsd']['VNFLinks']:
        # Search VNFs connected to vl
        connected_vnfs = []
        for vnf in scenario['nsd']['VNFs']:
            linked_cps = [cp for cp in vnf['CP']                      if 'VNFLink' in cp and cp['VNFLink']['id'] == vl['id']]
            if len(linked_cps) > 0:
                connected_vnfs.append(vnf['VNFid'])
        # Add all pairs VNF1---vl---VNF2
        for VNFe in list(combinations(connected_vnfs, 2)):
            vnf_graph.add_edge(VNFe[0],VNFe[1],weight=vl['required_capacity'])
    
    host_graph=nx.Graph()
    for e in scenario['nfvi']['LLs']:
        host_graph.add_edge(e['source']['id'],e['destination']['id'],weight=e['capacity']['total'])
    
    max_n=min(len(host_graph),len(vnf_graph))
    
    
    # We now have the two graphs (note that the library does not support directed graphs!) and the maximum number ``max_n`` of clusters to try. We can now compute the two dendograms (VNF and host).
    
    # In[61]:
    
    
    clusterer=GreedyAgglomerativeClusterer()
    dendo_vnf=clusterer.cluster(vnf_graph)
    dendo_host=clusterer.cluster(host_graph)
    
    
    # Now, for every value of $n$, we know which cluster each VNF and host belongs to. We write this information in the ``scenario`` data structure.
    
    # In[62]:
    
    
    scenario['clustering_decisions']=[]
    for n in range(1,max_n+1):
        this_decision={'no_clusters':n,'assignment_hosts':{},'assignment_vnfs':{}}
        print>>sys.stderr,'number of clusters is',n
        for h in host_graph:
            c_id=[i for i in range(n) if h in dendo_host.clusters(n)[i]][0]
            print>>sys.stderr,'  host',h,'belongs to cluster no.',c_id+1
            this_decision['assignment_hosts'][h]='host_cluster_'+str(c_id+1)
        for v in vnf_graph:
            c_id=[i for i in range(n) if v in dendo_vnf.clusters(n)[i]][0]
            print>>sys.stderr,'  VNF',v,'belongs to cluster no.',c_id+1
            this_decision['assignment_vnfs'][v]='vnf_cluster_'+str(c_id+1)
        # We do not check feasibility
        # this_decision['prima_facie_feasible']=prima_facie_feasible(dendo_host.clusters(n),dendo_vnf.clusters(n))
        scenario['clustering_decisions'].append(this_decision)
    
    
    # In[63]:
    
    
    scenario['clustering_decisions']
    
    
    # Now we can save our output file, i.e., a version of the scenario including the ``clustering_decisions`` data structure.
    
    # In[36]:
    
    
    # with open(output_path,'w') as fp:
    #     json.dump(scenario,fp,indent=2)
    return scenario
    
    
