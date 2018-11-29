import json
import networkx as nx
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__),
    '../../generator/src/vnfsMapping'))
from NS import *


def nfvi_pop_costs(pa_req, nfvi_pop_id):
    """Obtains the costs of mapping certain VNFs in the NFVI PoP

    :pa_req: API PARequest dictionary
    :nfvi_pop: unique string with the NFVI PoP id
    :returns: dictionary of costs indexed by vnf_name

    """
    costs = {}
    for cost in pa_req['nfvi']['VNFCosts']:
        if cost['NFVIPoPid'] == nfvi_pop_id:
            costs[cost['vnfid']] = cost['cost']

    return costs


def create_ns_graph(pa_req):
    """Creates a networkX multi-graph containing a NS

    :pa_req: API PARequest dictionary
    :returns: networkX multi-graph

    """
    ns_graph = nx.MultiGraph()

    for vnf in pa_req['nsd']['VNFs']:
        if 'place_at' not in vnf:
            vnf['place_at'] = []
        ns_graph.add_node(vnf['VNFid'], **vnf)

    vl_idx = 0
    for vnf_edge in pa_req['nsd']['VNFLinks']:
        vnf_edge['PAReqIndex'] = vl_idx
        vl_idx += 1
        ns_graph.add_edge(vnf_edge['source'], vnf_edge['destination'],
                **vnf_edge)

    return ns_graph


def get_vls(ns_graph):
    """Obtains the VLs present in the NS graph with their information

    :ns_graph: networkx multi-graph with NS information
    :returns: a dictionary indexed as (VNFid1, VNFid2, key)

    """

    vls = {}
    
    req_cap = nx.get_edge_attributes(ns_graph, "required_capacity")
    trav_probs = nx.get_edge_attributes(ns_graph, "traversal_probability")
    pa_req_idx = nx.get_edge_attributes(ns_graph, "PAReqIndex")
    sources = nx.get_edge_attributes(ns_graph, "source")
    destinations = nx.get_edge_attributes(ns_graph, "destination")


    for vl in req_cap:
        vls[vl] = {
            "required_capacity": req_cap[vl],
            "traversal_probability": trav_probs[vl],
            "PAReqIndex": pa_req_idx[vl],
            "source": sources[vl],
            "destination": destinations[vl]
        }

    return vls


def get_lls(nfvi_pops_graph):
    """Obtains the VLs present in the NS graph with their information

    :nfvi_pops_graph: networkx multi-graph with NFVI PoPs information
    :returns: a dictionary indexed as (NFVIPoP1, NFVIPoP2, key)

    """

    lls = {}
    
    cap = nx.get_edge_attributes(nfvi_pops_graph, "capacity")
    delay = nx.get_edge_attributes(nfvi_pops_graph, "delay")
    llid = nx.get_edge_attributes(nfvi_pops_graph, "LLid")
    mappedVLs = nx.get_edge_attributes(nfvi_pops_graph, "mappedVLs")
    PAReqIndex = nx.get_edge_attributes(nfvi_pops_graph, "PAReqIndex")


    for ll in cap:
        lls[ll] = {
            "capacity": cap[ll],
            "delay": delay[ll],
            "LLid": llid[ll],
            "mappedVLs": mappedVLs[ll],
            "PAReqIndex": PAReqIndex[ll]
        }

    return lls


def create_nfvi_pop_graph(pa_req):
    """Creates the NFVI PoPs graph based on the PARequest of the API

    :pa_req: API PARequest dictionary
    :returns: networkX multi-graph

    """
    infra_graph = nx.MultiGraph()

    for nfvi_pop in pa_req['nfvi']['NFVIPoPs']:
        nfvi_pop['costs'] = nfvi_pop_costs(pa_req, nfvi_pop['id'])
        nfvi_pop['mappedVNFs'] = []
        for intra_vl_cost in pa_req['nfvi']['VLCosts']:
            if intra_vl_cost['NFVIPoP'] == nfvi_pop['id']:
                nfvi_pop['VLCost'] = intra_vl_cost['cost']
        infra_graph.add_node(nfvi_pop['id'], **nfvi_pop)

    pa_req_ll_idx = 0
    for ll in pa_req['nfvi']['LLs']:
        ll['mappedVLs'] = []
        ll['PAReqIndex'] = pa_req_ll_idx
        pa_req_ll_idx += 1
        for ll_cost in pa_req['nfvi']['LLCosts']:
            if ll_cost['LL'] == ll['LLid']:
                ll['cost'] = ll_cost['cost']
        infra_graph.add_edge(ll['source']['id'], ll['destination']['id'],
            **ll)

    return infra_graph


def create_nfvi_pop_clusters(pa_req):
    """Creates a list of host clusters based on the API PA Request

    :pa_req: API PARequest dictionary
    :returns: dictionary of networkX graphs representing host clusters.
              Indexed by cluster number

    """
    nfvi_pop_clusters = {}

    # Add the cluster nodes
    for nfvi_pop in pa_req['nfvi']['NFVIPoPs']:
        if nfvi_pop['cluster'] not in nfvi_pop_clusters:
            nfvi_pop_clusters[nfvi_pop['cluster']] = nx.MultiGraph()
        for intra_vl_cost in pa_req['nfvi']['VLCosts']:
            if intra_vl_cost['NFVIPoP'] == nfvi_pop['id']:
                nfvi_pop['VLCost'] = intra_vl_cost['cost']
        nfvi_pop['costs'] = nfvi_pop_costs(pa_req, nfvi_pop['id'])
        nfvi_pop['mappedVNFs'] = []
        nfvi_pop_clusters[nfvi_pop['cluster']].add_node(nfvi_pop['id'],
                **nfvi_pop)

    # Add the clusters links
    paReqIndex = 0
    for ll in pa_req['nfvi']['LLs']:
        # Extra params derived from the JSON PAReq
        ll['PAReqIndex'] = paReqIndex
        ll['mappedVLs'] = []
        for ll_cost in pa_req['nfvi']['LLCosts']:
            if ll_cost['LL'] == ll['LLid']:
                ll['cost'] = ll_cost['cost']
        paReqIndex += 1

        for cluster_num in nfvi_pop_clusters:
            cluster = nfvi_pop_clusters[cluster_num]
            cluster_hosts = cluster.nodes()
            if ll['source']['id'] in cluster_hosts and\
                ll['destination']['id'] in cluster_hosts:
                cluster.add_edge(ll['source']['id'], ll['destination']['id'],
                        **ll)

    return nfvi_pop_clusters


def create_ns_clusters(pa_reqs):
    """Creates a list of VNF clusters based on the API PA Request

    :pa_reqs: a list of API PARequest dictionary
    :returns: dictionary of networkX graphs representing VNF clusters.
              Indexed by cluster number

    """
    ns_clusters = {}

    # Add the cluster nodes 
    for pa_req in pa_reqs:
        for vnf in pa_req['nsd']['VNFs']:
            if vnf['cluster'] not in ns_clusters:
                ns_clusters[vnf['cluster']] = nx.MultiGraph()
            if 'place_at' not in vnf:
                vnf['place_at'] = []
            ns_clusters[vnf['cluster']].add_node(vnf['VNFid'], **vnf)

    # Add the cluster edges
    for pa_req in pa_reqs:
        reqIdx = 0
        for edge in pa_req['nsd']['VNFLinks']:
            edge['PAReqIndex'] = reqIdx
            reqIdx += 1
            for cluster_num in ns_clusters:
                cluster = ns_clusters[cluster_num]
                cluster_vnfs = cluster.nodes()

                if edge['source'] in cluster_vnfs and\
                    edge['destination'] in cluster_vnfs:
                        cluster.add_edge(edge['source'], edge['destination'],
                            **edge)

    return ns_clusters


def get_nfvi_pop(nfvi_pop_graph, nfvi_pop_id):
    """Retrieves a node dictionary with all the NFVI PoP properties

    :nfvi_pop_graph: networkX multi-graph
    :nfvi_pop_id: NFVI PoP unique identifier
    :returns: dictionary with all the NFVI PoP properties

    """
    return {
        'cluster': nx.get_node_attributes(nfvi_pop_graph,
            'cluster')[nfvi_pop_id],
        'id': nfvi_pop_id,
        'capabilities': nx.get_node_attributes(nfvi_pop_graph,
			'capabilities')[nfvi_pop_id],
        'availableCapabilities': nx.get_node_attributes(nfvi_pop_graph,
            'availableCapabilities')[nfvi_pop_id],
        'mappedVNFs': nx.get_node_attributes(nfvi_pop_graph,
			'mappedVNFs')[nfvi_pop_id],
        'costs': nx.get_node_attributes(nfvi_pop_graph,
            'costs')[nfvi_pop_id],
        'location': nx.get_node_attributes(nfvi_pop_graph,
            'location')[nfvi_pop_id],
        'VLCost': nx.get_node_attributes(nfvi_pop_graph,
            'VLCost')[nfvi_pop_id]
    }


def get_vnf(ns_graph, vnf_id):
    """Obtains the VNF node dictionary with all its properties

    :ns_graph: networkX multi-graph instance
    :vnf_id: VNF ID unique identifier
    :returns: dictionary with all the VNF properties

    """
    asCluster = nx.get_node_attributes(ns_graph, "nfviPoPCluster")
    asCluster = asCluster[vnf_id] if vnf_id in asCluster else "NULL"

    vnf_dict = {
        "VNFid": vnf_id,
        "processing_latency": nx.get_node_attributes(ns_graph,
    		'processing_latency')[vnf_id],
    	"place_at": nx.get_node_attributes(ns_graph,
    		'place_at')[vnf_id],
    	"requirements": nx.get_node_attributes(ns_graph,
    		'requirements')[vnf_id],
    	"cluster": nx.get_node_attributes(ns_graph,
    		'cluster')[vnf_id],
        "location": nx.get_node_attributes(ns_graph,
    		'location')[vnf_id],
        "nfviPoPCluster": asCluster
    }

    if vnf_id in nx.get_node_attributes(ns_graph, 'host_cluster'):
        vnf_dict['host_cluster'] =\
            nx.get_node_attributes(ns_graph, 'host_cluster')[vnf_id]

    return vnf_dict


def map_vnf(ns_graph, nfvi_pops_graph, vnf_name, nfvi_pop_id):
    """Maps a VNF to an NFVI PoP node. Free resources are consumed in the
    corresponding nfvi_pops_graph node.

    :ns_graph: networkX multi-graph instance
    :nfvi_pops_graph: networkX multi-graph
    :vnf_name: VNF name unique identifier
    :nfvi_pop_id: host name unique identifier
    :returns: Nothing

    """
    vnf_node = get_vnf(ns_graph, vnf_name)
    nfvi_pop = get_nfvi_pop(nfvi_pops_graph, nfvi_pop_id)
    
    for req in vnf_node['requirements']:
        nfvi_pop['availableCapabilities'][req] -= vnf_node['requirements'][req]


def map_vnfs_edge(ns_graph, nfvi_pop_graph, vnfs_edge, nfvi_pop_path):
    """Maps the vnfs edge resources to the LLs contained inside the
    nfvi_pop_path

    :ns_graph: networkX multi-graph instance
    :nfvi_pop_graph: networkX multi-graph
    :vnfs_edge: ('vnf_id1', 'vnf_id2', mVl)
    :nfvi_pop_path: [('nfvi_pop_id1', 'nfvi_pop_id2', mLl), ...]
    :returns: Nothing

    """
    vnf1, vnf2, mVl = vnfs_edge

    for (nfvi_pop1, nfvi_pop2, mLl) in nfvi_pop_path:
        nfvi_pop_graph[nfvi_pop1][nfvi_pop2][mLl]['capacity']['available'] -=\
            ns_graph[vnf1][vnf2][mVl]['required_capacity']


def free_vnf(ns_graph, infra_graph, vnf_id, nfvi_pop_id):
    """Frees the VNF resources in a host node. Free resources are increased in
    the infra_graph node.

    :ns_graph: networkX multi-graph instance
    :infra_graph: networkX multi-graph
    :vnf_id: VNF unique identifier
    :nfvi_pop_id: NFVI PoP unique identifier
    :returns: Nothing

    """
    vnf_node = get_vnf(ns_graph, vnf_id)
    nfvi_pop = get_nfvi_pop(infra_graph, nfvi_pop_id)
    
    for req in vnf_node['requirements']:
        nfvi_pop['availableCapabilities'][req] += vnf_node['requirements'][req]


# TODO - UNUSED -> DELETE
def map_vnf_edge(vnfs_graph, hosts_graph, vnf_edge, hosts_edges):
    """Maps the vnf_edge resources to a list of host edges. Host edge resources
    consumption is stored inside the hosts_graph.

    :vnfs_graph: networkX graph instance
    :hosts_graph: networkX graph
    :vnf_edge: vnf edge ('vnf_name1', 'vnf_name2')
    :hosts_edges: list of host edges [('host_name1', 'host_name2'), ...]
    :returns: Nothing

    """
    traffic = vnfs_graph.edges()[vnf_edge[0]][vnf_edge[1]]
    for h1_name, h2_name in hosts_edges:
        hosts_edges.edges()[h1_name][h2_name]['free_capacity'] -= traffic


# TODO - UNUSED -> DELETE
def unmap_vnf_edge(vnfs_graph, hosts_graph, vnf_edge, hosts_edges):
    """Unmaps the vnf_edge resources in a list of host edges. Host edge resources
    consumption is freed inside the hosts_graph.

    :vnfs_graph: networkX graph instance
    :hosts_graph: networkX graph
    :vnf_edge: vnf edge ('vnf_name1', 'vnf_name2')
    :hosts_edges: list of host edges [('host_name1', 'host_name2'), ...]
    :returns: Nothing

    """
    traffic = vnfs_graph.edges()[vnf_edge[0]][vnf_edge[1]]
    for h1_name, h2_name in hosts_edges:
        hosts_edges.edges()[h1_name][h2_name]['free_capacity'] += traffic


def costs_dict(pa_req):
    """Obtains a cost dictionary of vnf-to-host mapping cost

    :pa_req: pa_req object from an API request
    :returns: dictionary with costs indexed as: {(vnf_id, nfvi_pop_id): cost}

    """
    costs = {}
    for cost in pa_req['VNFCosts']:
        costs[(cost['vnfid'], cost['NFVIPoPid'])] = cost['cost']

    return costs


def ns_cluster_vnf_req(ns_cluster):
    """Aggregates the VNF requirements of a NS cluster

    :ns_cluster: networkX NS cluster multi-graph
    :returns: dictionary adding requirements of VNFs inside the cluster

    """
    vnfs_req = nx.get_node_attributes(ns_cluster, 'requirements')
    cluster_reqs = {}
    
    # Initialize cluster requirements dictionary
    for req in vnfs_req[vnfs_req.keys()[0]]:
        cluster_reqs[req] = 0

    # Add all VNFs requirements
    for vnf_id in vnfs_req:
        for req in cluster_reqs:
            cluster_reqs[req] += vnfs_req[vnf_id][req]

    return cluster_reqs


def ns_cluster_edge_req(ns_cluster):
    """Obtains the aggregated requirements of the edges inside the NS cluster
    Note: delay requirements are not added because is not a consumed resource
          for the moment we only consider the traffic as a requirement

    :ns_cluster: networkX NS cluster multi-graph
    :returns: dictionary adding requirements of edges inside the cluster

    """
    traffic = 0
    for (vnf_id2, vnf_id1, mVl) in get_vls(ns_cluster):
        traffic += ns_cluster[vnf_id1][vnf_id2][mVl]['required_capacity']

    return { 'traffic': traffic }


def nfvi_pop_cluster_cap(nfvi_pop_cluster):
    """Aggregates the capabilities of a NFVI PoP cluster

    :nfvi_pop_cluster: NFVI PoP cluster
    :returns: dictionary adding capabilities of hosts inside the cluster

    """
    nfvi_pop_cap = nx.get_node_attributes(nfvi_pop_cluster, 'capabilities')
    cluster_cap = {}

    # Initialize cluster requirements dictionary
    for req in nfvi_pop_cap[nfvi_pop_cap.keys()[0]]:
        cluster_cap[req] = 0

    # Add all NFVI PoPs capabilities
    for host_name in nfvi_pop_cap:
        for req in cluster_cap:
            cluster_cap[req] += nfvi_pop_cap[host_name][req]

    # Add LLs bandwidth
    for (nfvi_pop1, nfvi_pop2, mLl) in get_lls(nfvi_pop_cluster):
        ll = nfvi_pop_cluster[nfvi_pop1][nfvi_pop2][mLl]
        cluster_cap['bandwidth'] += ll['capacity']['total']

    return cluster_cap


def nfvi_pop_cluster_free_cap(nfvi_pop_cluster):
    """Aggregates the host free capabilities of a NFVI PoP cluster

    :nfvi_pop_cluster: NFVI PoP cluster
    :returns: dictionary adding free capabilities of NFVI PoPs inside the
    cluster

    """
    nfvi_pop_free_cap = nx.get_node_attributes(nfvi_pop_cluster,
            'availableCapabilities')
    cluster_free_cap = {}
    
    # Initialize cluster requirements dictionary
    for req in nfvi_pop_free_cap[nfvi_pop_free_cap.keys()[0]]:
        cluster_free_cap[req] = 0

    # Add all VNFs requirements
    for nfvi_pop_id in nfvi_pop_free_cap:
        for req in cluster_free_cap:
            cluster_free_cap[req] += nfvi_pop_free_cap[nfvi_pop_id][req]

    # Add LLs bandwidth
    for (nfvi_pop1, nfvi_pop2, mLl) in get_lls(nfvi_pop_cluster):
        ll = nfvi_pop_cluster[nfvi_pop1][nfvi_pop2][mLl]
        cluster_free_cap['bandwidth'] += ll['capacity']['available']

    return cluster_free_cap


def nfvi_pop_cluster_free_bw(nfvi_pop_cluster):
    """Obtains the aggregated NFVI PoP cluster bandwidth

    :nfvi_pop_cluster: networkX multi-graph NFVI PoP cluster
    :returns: dictionary adding capabilities of LLs inside the cluster

    """
    cap = 0

    for (nfvi_pop1, nfvi_pop2, mLl) in get_lls(nfvi_pop_cluster):
        cap += nfvi_pop_cluster[nfvi_pop1][nfvi_pop2][\
mLl]['capacity']['available']

    for nfvi_pop_id in nfvi_pop_cluster.nodes():
        nfvi_pop = get_nfvi_pop(nfvi_pop_cluster, nfvi_pop_id)
        cap += nfvi_pop['availableCapabilities']['bandwidth']

    return { 'traffic': cap }


def enough_cluster_res(ns_cluster, nfvi_pop_cluster):
    """Checks if there are enough aggregated cluster resources for the NS
    cluster inside the passed NFVI PoP cluster

    :ns_cluster: networkX multo-graph NS cluster
    :nfvi_pop_cluster: networkX multi-graph NFVI PoP cluster
    :returns: boolean

    """
    # Check if there are enough computational resources
    enough_cl_res = True
    ns_cl_req = ns_cluster_vnf_req(ns_cluster)
    nfvi_pop_cl_free_cap = nfvi_pop_cluster_free_cap(nfvi_pop_cluster)
    for req in ns_cl_req:
        enough_cl_res = enough_cl_res and\
            ns_cl_req[req] <= nfvi_pop_cl_free_cap[req]

    if not enough_cl_res:
        return False


    # Check if enough edge resources
    ns_edge_req = ns_cluster_edge_req(ns_cluster)
    nfvi_pop_cl_ll_cap = nfvi_pop_cluster_free_bw(nfvi_pop_cluster)

    for req in ns_edge_req:
        enough_cl_res = enough_cl_res and\
            ns_edge_req[req] < nfvi_pop_cl_ll_cap[req]

    return enough_cl_res


def can_host_vnf(nfvi_pop_node, vnf_node):
    """Checks if a NFVI PoP can instantiate a vnf inside

    :nfvi_pop_node: NFVI PoP dict having: {'availableCapabilities':{},
    'costs': {'vnf_1':2}}
    :vnf_node: VNF dict having: {'requirements':{}, 'vnf_id'}
    :returns: boolean

    """
    # Check if VNF is supported
    if vnf_node['VNFid'] not in nfvi_pop_node['costs']:
        return False

    i = 0
    enough_res = True
    nfvi_pop_free_capabilities = nfvi_pop_node['availableCapabilities']
    vnf_requirements = vnf_node['requirements']
    resources_list = vnf_requirements.keys()

    # Check if host has enough resources
    while enough_res and i < len(resources_list):
        res = resources_list[i]
        if nfvi_pop_free_capabilities[res] < vnf_requirements[res]:
            enough_res = False
        else:
            i += 1

    return enough_res


def exist_capable_nfvi_pop(vnf_node, nfvi_pop_graph):
    """Determine if it exists a NFVI PoP capable of hosting the VNF

    :vnf_node: VNF dict having: {'requirements':{}, 'vnf_name'}
    :nfvi_pop_graph: networkX NFVI PoP multi-graph (full or cluster view)
    :returns: (boolean, nfvi_pop_id)

    """
    nfvi_pops_ids = nfvi_pop_graph.nodes()
    i = 0
    found_host, nfvi_pop_id = False, None
    while not found_host and i < len(nfvi_pops_ids):
        nfvi_node = get_nfvi_pop(nfvi_pop_graph, nfvi_pops_ids[i])
        found_host = can_host_vnf(nfvi_node, vnf_node)
        if not found_host:
            i += 1
        else:
            nfvi_pop_id = nfvi_pops_ids[i]

    return found_host, nfvi_pop_id


def can_host_link(nfvi_pop_graph, ns_graph, ll, vl):
    """Checks if a VNF edge can be mapped to a host edge

    :nfvi_pop_graph: networkX NFVI PoPs multi-graph (all or cluster view)
    :ns_graph: networkX VNFs graph (all or cluster view)
    :ll: (nfvi_id1, nfvi_id2, mLl)
    :vl: (vnf_id1, vnf_id2, mVl)
    :returns: boolean

    """
    nfvi_id1, nfvi_id2, mLl = ll
    vnf_id1, vnf_id2, mVl = vl
    free_cap = nfvi_pop_graph.get_edge_data(nfvi_id1,
            nfvi_id2)[mLl]['capacity']['available']
    req_cap = ns_graph.get_edge_data(vnf_id1,
            vnf_id2)[mVl]['required_capacity']

    return free_cap >= req_cap


def exist_capable_edge(nfvi_pop_graph, ns_graph, vl):
    """Determines if it exists a LL capable of allocating the vl

    :nfvi_pop_graph: networkX NFVI PoP multi-graph (all or cluster view)
    :ns_graph: networkX NS multi-graph (all or cluster view)
    :vl: (vnf_id1, vnf_id2, mVl)
    :returns: (boolean, (nfvi_pop1, nfvi_pop2))

    """
    i = 0
    found_edge, nfvi_pops_edge = False, None
    llsk = get_lls(nfvi_pop_graph).keys() # Obtain the LLs' keys

    while not found_edge and i < len(llsk):
        found_edge = can_host_link(nfvi_pop_graph, ns_graph, llsk[i], vl)
        if not found_edge:
            i += 1
        else:
            nfvi_pops_edge = llsk[i]

    return found_edge, nfvi_pops_edge


def fake_cluster_cap_reduction(nfvi_pop_graph, cap_reduction):
    """Performs a capabilities reduction affecting only a single host and link
    (if existing). It can even put negative values. The purpose is to reduce
    the overall cluster capacities for the hosts_cluster_free_cap() collection.

    :nfvi_pop_graph: networkX NFVI PoPs multi-graph
    :cap_reduction: dictionary with link and host capacities to be reduced {'link': {'capA': , 'capB'}, 'host': {'capA': , ...}}
    :returns: Nothing

    """
    nfvi_pop1 = nfvi_pop_graph.nodes()[0]

    # Reduce host resources
    nfvi_pop1_res = nx.get_node_attributes(nfvi_pop_graph,
            'availableCapabilities')[nfvi_pop1]
    for capability in cap_reduction['host']:
        nfvi_pop1_res[capability] -= cap_reduction['host'][capability]

    # Reduce link resources
    if len(nfvi_pop_graph.edges()) > 0:
        nfvi_pop1, nfvi_pop2 = nfvi_pop_graph.edges()[0]
        for cap in cap_reduction['link']:
            if cap == 'traffic':
                nfvi_pop_graph[nfvi_pop1][nfvi_pop2][0]['capacity']\
                    ['available'] -= cap_reduction['link'][cap]
            else:
                nfvi_pop_graph[nfvi_pop1][nfvi_pop2][0][cap] -=\
                    cap_reduction['link'][cap]


def cluster_match_cost(ns_cluster, nfvi_pop_cluster):
    """Retrieves the cost resulting in mapping a NS cluster to the
    infrastructure cluster

    :ns_cluster: networkX multi-graph NS cluster instance
    :nfvi_pop_cluster: networkX NFVI PoPs multi-graph cluster instance
    :note: the VLs cost considered are the intra-domain ones
    :returns: float number with the cost

    """
    cost = float(0)
    vnfs = ns_cluster.nodes()
    avg_vnf_cost = {}
    for vnf in vnfs:
        avg_vnf_cost[vnf] = []

    # VNF average mapping cost
    for nfvi_pop_id in nfvi_pop_cluster.nodes():
        nfvi_pop_costs_ = nx.get_node_attributes(nfvi_pop_cluster,
                'costs')[nfvi_pop_id]
        for vnf in nfvi_pop_costs_:
            if vnf in vnfs:
                avg_vnf_cost[vnf].append(nfvi_pop_costs_[vnf])
    avg_costs = []
    for vnf in vnfs:
        avg_costs.append(reduce(lambda x, y: x + y, avg_vnf_cost[vnf])\
            / float(len(avg_vnf_cost[vnf])))
    vnf_avg_cost = reduce(lambda x, y: x + y, avg_costs)

    # Average mapping cost of all VLs inside a single NFVI PoP 
    nfvi_pops_intra_avg = 0
    for nfvi_pop_id in nfvi_pop_cluster.nodes():
        nfvi_pop = get_nfvi_pop(nfvi_pop_cluster, nfvi_pop_id)

        for (vnf_id1, vnf_id2, mVl) in get_vls(ns_cluster):
            vl = ns_cluster[vnf_id1][vnf_id2][mVl]
            nfvi_pops_intra_avg +=\
                (vl['required_capacity'] *\
                nfvi_pop['VLCost'] /\
                1.0) / len(nfvi_pop_cluster.nodes())

    # Average mapping cost of all VLs within the LLs
    lls_inter_avg = 0
    num_LLs = 0
    for (nfvi_pop1, nfvi_pop2, mLl) in get_lls(nfvi_pop_cluster):
        ll = nfvi_pop_cluster[nfvi_pop1][nfvi_pop2][mLl]
        for (vnf_id1, vnf_id2, mVl) in get_vls(ns_cluster):
            vl = ns_cluster[vnf_id1][vnf_id2][mVl]
            lls_inter_avg += vl['required_capacity'] * ll['cost']
        num_LLs += 1
    # If the cluster has LLs, get average cost
    if num_LLs > 0:
        lls_inter_avg = (lls_inter_avg / 1.0) / num_LLs

    return vnf_avg_cost + nfvi_pops_intra_avg + lls_inter_avg


def get_vnfs_dict(pa_req):
    """Converts the VNFs list in the pa_req into a dictionary indexed by
    their IDs.

    :pa_req: API PARequest dictionary
    :returns: {'vnf_id1': {...}, ...}

    """
    vnfs_dict = {}
    for vnf in pa_req['nsd']['VNFs']:
        vnfs_dict[vnf['VNFid']] = vnf

    return vnfs_dict


def get_inter_cluster_vl(ns_graph):
    """Obtains the VLs connecting VNFs in separate NS clusters

    :ns_graph: NetworkX multi-graph for the NS
    :returns: list of VLs as VNF id pairs: [('vnf1', 'vnf2', mVl), ...]

    """
    inter_cluster_vl = []

    vls = get_vls(ns_graph)
    for vl in vls:
        vnf1 = get_vnf(ns_graph, vl[0])
        vnf2 = get_vnf(ns_graph, vl[1])

        if vnf1['cluster'] != vnf2['cluster']:
            inter_cluster_vl.append(vl)

    return inter_cluster_vl


def persist_vnf_path_map(pa_req, nfvi_pops_graph, ns_graph, vl,
        nfvi_pops_path):
    """Stores in the PAReq API JSON the mapping from VLs to the LLs

    :pa_req: API PARequest dictionary
    :nfvi_pops_graph: networkX multi-graph with NFVI PoPs
    :ns_graph: networkX VNFs multi-graph (all or cluster view)
    :vl: ('vnf_id1', 'vnf_id2', mVl)
    :nfvi_pops_path: [('nfvi_pop_id1', 'nfvi_pop_id2', mLl), ...]
    :returns: the updated PAReq API JSON

    :note1: it assumes that the nfvi_pops_graph resources have already been
    reduced. It just copies nfvi_pops_graph available resources to the pa_req.
    The reason behind this is that pa_req and the nfvi_pops_graph might be
    referencing to the same object, hence if a ns_graph was previously reduced
    it might be the case that the pa_req as well due to this.
    :note2: the mappedVLs dictionary is updated in the pa_req

    """
    vnf_id1, vnf_id2, mVl = vl
    vlObj = get_vls(ns_graph)[vl]

    # Update API PARequest pa_req
    lls = get_lls(nfvi_pops_graph)
    for ll in nfvi_pops_path:
        if ll not in lls:
            ll = (ll[1], ll[0], ll[2])
        llObj = lls[ll]
        pa_req_ll = pa_req['nfvi']['LLs'][llObj['PAReqIndex']]
        pa_req_ll['capacity']['available'] = llObj['capacity']['available']

        if 'mappedVLs' not in pa_req_ll:
            pa_req_ll['mappedVLs'] = []
        pa_req_ll['mappedVLs'].append({
            'src': vlObj['source'],
            'dst': vlObj['destination'],
            'PAReqVLIndex': vlObj['PAReqIndex']
        })

    return pa_req


def mapping_costs(pa_req):
    """Obtains the mapping costs present in the pa_req.
    It writes a "mapping_cost" field in the pa_req root.

    :pa_req: API PARequest dictionary
    :returns: total mapping cost of the pa_req

    """
    total_cost = 0
    costs = costs_dict(pa_req)
    for nfvi_pop in pa_req['nfvi']['NFVIPoPs']:
        for mapped_vnf in nfvi_pop['mappedVNFs']:
            total_cost += costs[(mapped_vnf, nfvi_pop['id'])]
    pa_req['totalCost'] = total_cost

    return total_cost


def mapping_costs_place_at(pa_req):
    """Obtains the mapping costs from a API PARequest whith only the
    place_at key set in the JSON

    :pa_req: API PARequest dictionary
    :returns: total mapping cost

    """
    costs_dict_ = costs_dict(pa_req)
    cost = 0
    for vnf in pa_req['nsd']['VNFs']:
        for nfvi_pop in vnf['place_at']:
            cost += costs_dict_[(vnf['VNFid'], nfvi_pop)]
    
    return cost


#######################
## TODO - until here ##
#######################
# TODO 2 - consider that switches can happen
#          probably during the nfvi pop cluster creation
#          and in the edges related functions


def mapped_ns_delays(pa_req):
    """Obtains the delay of the NS mapped

    :pa_req: API PARequest dictionary
    :returns: updated pa_req with "mapping_delay" inside the service

    """
    infra_graph = create_nfvi_pop_graph(pa_req)
    ns_graph = create_ns_graph(pa_req)
    ns_mapped_delays = {}

    # All delays to zero
    for (v1, v2, mVl) in get_vls(ns_graph):
        ns_graph[v1][v2][mVl]['delay'] = 0

    # Go through all VLs mapped accross NFVI PoPs
    for ll in pa_req['nfvi']['LLs']:
        for mapped_vl in ll['mappedVLs']:
            src = mapped_vl['src']
            dst = mapped_vl['destination']

            # Update the VNF edge delay
            if src in ns_graph:
                if dst in ns_graph[src]:
                    delay = ns_graph[src][dst][0]['delay']
                    nx.set_edge_attributes(ns_graph, 'delay',
                        {(src, dst, 0): delay + ll['delay']})
    #print '--- graph edges delays ---'
    #for edge in ns_graph.edges():
    #    print edge[0] + '-' + edge[1] + '(delay)=' +\
    #        str(ns_graph[edge[0]][edge[1]]['delay'])
    #print ''

    # Create a NS instance from the ns_graph
    first_vnf = filter(lambda v: 'v_gen_1_' in v, ns_graph.nodes())[0]
    vnfs = [{
        'processing_latency': 0,
        'vnf_name': 'start',
        'requirements': {}
    }]
    for vnf_id in ns_graph.nodes():
        vnf = get_vnf(ns_graph, vnf_id)
        vnf['vnf_id'] = vnf_id
        vnf['memory'] = 0
        vnf['disk'] = 0
        vnf['cpu'] = 0
        vnfs.append(vnf)
    vnf_vls = [{
        'idA': 'start',
        'idB': first_vnf,
        'bw': 0,
        'delay': 0,
        'prob': 1
    }]
    for (v1, v2, mVl) in get_vls(ns_graph):
        vl = ns_graph[v1][v2][mVl]
        vl['idA'], vl['idB'], vl['bw'] = v1, v2, 0
        vnf_vls.append(vl)
    ns = NS.create(vnfs, vnf_vls) # TODO - this method does not support
                                  #        multigraphs
    dd = ns.avgDelay() # TODO - this method does not support multigraphs
    ns_mapped_delays[pa_req['nsd']['id']] = dd

    # Update the PARequest with the delay
    i = 0
    pa_req['totalLatency'] = ns_mapped_delays[ns_mapped_delays.keys()[0]]
    # TODO - note that there is a single NS to be mapped, consider changing
    #        the function accordingly

    # Obtain averge overall mapping delay across services
    pa_req['avg_services_delay'] = pa_req['totalLatency']
    # TODO - there is only one service

    return pa_req



def mapping_cost(pa_req):
    """Obtains the mapping cost resulting of the PA API request with the 
    mapping decisions.

    :pa_req: PA API request with the mapping decisions inside
    :returns: the mapping cost of the decision present in the PA API request

    """
    vnf_cost = 0
    vls_cost = 0

    # Get the VNFs mapping cost
    vnf_map_costs = {}
    for vnf_map_cost in pa_req['nfvi']['VNFCosts']:
        vnf_map_costs[(vnf_map_cost['NFVIPoPid'], vnf_map_cost['vnfid'])] =\
            vnf_map_cost['cost']

    for nfvi_pop in pa_req['nfvi']['NFVIPoPs']:
        for vnf_id in nfvi_pop['mappedVNFs']:
            vnf_cost += vnf_map_costs[(nfvi_pop['id'], vnf_id)]


    # Get the VLs mapping cost
    vls_map_cost = {}
    for vl_map_cost in pa_req['nfvi']['LLCosts']:
        vls_map_cost[vl_map_cost['LL']] = vl_map_cost['cost']

    for ll in pa_req['nfvi']['LLs']:
        for mapped_vl in ll['mappedVLs']:
            vl_cap = pa_req['nsd']['VNFLinks'][mapped_vl['PAReqVLIndex']]\
['required_capacity']
            vls_cost += vls_map_cost[ll['LLid']] * vl_cap
            

    return vnf_cost + vls_cost


def integrate_decisions(pa_req, clust_idx = 0):
    """Integrate the clustering decisions made by the agglomerative clustering
    inside the PA API request.

    :pa_req: PA API request with the clustering decisions
    :clust_idx: clustering decision index
    :returns: Nothing (pa_req object is udpated)

    """
    decisions = pa_req['clustering_decisions'][clust_idx]

    # Integrate NFVI PoPs cluster assignments
    for nfvi_pop in pa_req['nfvi']['NFVIPoPs']:
        nfvi_pop['cluster'] = decisions['assignment_hosts'][nfvi_pop['id']]
    for vnf in pa_req['nsd']['VNFs']:
        vnf['cluster'] = decisions['assignment_vnfs'][vnf['VNFid']]


def req_to_resp(pa_req):
    """Translates a PA API request with decisions into a PA API response.

    :pa_req: PA API request with the clustering decisions
    :returns: PA API response dictionary

    """
    pa_resp = {}

    # Add the NFVI PoPs used in the mapping
    vnf_maps = {}
    pa_resp['usedNFVIPoPs'] = []
    for nfvi_pop in pa_req['nfvi']['NFVIPoPs']:
        if len(nfvi_pop["mappedVNFs"]) > 0:
            pa_resp['usedNFVIPoPs'].append({
                "NFVIPoPID": nfvi_pop["id"],
                "mappedVNFs": nfvi_pop["mappedVNFs"]
            })
            for vnf in nfvi_pop["mappedVNFs"]:
                if vnf not in vnf_maps:
                    vnf_maps[vnf] = nfvi_pop['id']


    # Init dict of VLs that are not mapped to LLs, and dict of VLs
    vls, vl_no_ll = {}, {}
    for i in len(pa_req['nsd']['VNFLinks']):
        vl = pa_req['nsd']['VNFLinks'][i]
        vl_no_ll[vl['id']] = True
        vls[vl['id']] = vl


    # Add the LLs used in the mapping
    pa_resp["usedLLs"] = []
    for ll in pa_req['nfvi']['LLs']:
        if len(ll['mappedVLs']) > 0:
            mappedVLs = [vl['id'] for vl in ll['mappedVLs']]

            # Update list of VLs not mapped to LLs
            for vl in mappedVLs:
                if vl in vl_no_ll:
                    del vl_no_ll[vl]

            pa_resp['usedLLs'].append({
                "LLID": ll['LLid'],
                "mappedVLs": mappedVLs
            })

    # Add the VLs not mapped to LLs
    pa_resp['usedVLs'] = []
    nfvi_pop_vls = {}
    for vl_id in vl_no_ll:
        vl = vls[vl_id]
        asoc_nfvi_pop = vnf_maps[vl['source']]
        if asoc_nfvi_pop not in nfvi_pop_vls:
            nfvi_pop_vls[asoc_nfvi_pop] = []
        nfvi_pop_vls[asoc_nfvi_pop].append(vl_id)
    for nfvi_pop_id in nfvi_pop_vls:
        pa_resp['usedVLs'].append({
            'NFVIPoP': nfvi_pop_id,
            'mappedVLs': nfvi_pop_vls[nfvi_pop_id]
        })

    # Deployment cost and latencies
    pa_resp['totalCost'] = mapping_cost(pa_req)
    pa_resp['totalLatency'] = 0 # TODO - impossible without traversal order 


def result2PAResponse(garrota_result):
    """Translates the garrota algorithm result into a PAResponse

    :garrota_result: dictionary with the garrota PA result
    :returns: PAResponse dictionary

    """
    if garrota_result == None:
        return { 'worked': False, 'result': 'No placement possible' }

    pa_response = {}
    used_nfvi_pops = []
    used_lls = []

    # Fill the used NFVI PoPs
    mapped_vnfs_ = {}
    for nfvi_pop in garrota_result['nfvi']['NFVIPoPs']:
        mapped_vnfs = nfvi_pop['mappedVNFs']
        if len(mapped_vnfs) > 0:
            mapped_vnf_ids = []
            for mapped_vnf in mapped_vnfs:
                mapped_vnfs_[mapped_vnf] = nfvi_pop['id']
                mapped_vnf_ids.append(mapped_vnf)
            used_nfvi_pops.append({
                'NFVIPoPID': nfvi_pop['id'],
                'mappedVNFs': mapped_vnf_ids
            })
    pa_response['usedNFVIPops'] = used_nfvi_pops

    # Fill the used LLs
    mapped_vls_ = {}
    for ll in garrota_result['nfvi']['LLs']:
        mapped_vls = ll['mappedVLs']
        if len(mapped_vls) > 0:
            mapped_vl_ids = []
            # Insert the VL id and report it is mapped to a LL
            for i in range(len(mapped_vls)):
                vl_idx = mapped_vls[i]['PAReqVLIndex']
                vl = garrota_result['nsd']['VNFLinks'][vl_idx]
                mapped_vls[i]['id'] = vl['id']
                mapped_vls_[vl['id']] = True
                mapped_vl_ids.append(vl['id'])
            used_lls.append({
                'LLID': ll['LLid'],
                'mappedVLs': mapped_vl_ids
            })
    pa_response['usedLLs'] = used_lls

    # Fill the used VLs (VLs not mapped at any LL)
    usedVLs_ = {}
    for vl in garrota_result['nsd']['VNFLinks']:
        if vl['id'] not in mapped_vls_:
            assoc_nfvi_id = mapped_vnfs_[vl['source']]
            if assoc_nfvi_id not in usedVLs_:
                usedVLs_[assoc_nfvi_id] = []
            usedVLs_[asssoc_nfvi_id].append(vl['id'])
    usedVLs = []
    for nfvi_pop_id in usedVLs_:
        usedVLs.append({
            'NFVIPoP': nfvi_pop_id,
            'mappedVLs': usedVLs_[nfvi_pop_id].keys()
        })
    pa_response['usedVLs'] = usedVLs

    # TODO -total latency still not possible to obtain
    pa_response['totalLatency'] = -1
    pa_response['totalCost'] = garrota_result['totalCost']

    pa_response['worked'] = True
    pa_response['result'] = 'Placement algorithm success'

    return pa_response

