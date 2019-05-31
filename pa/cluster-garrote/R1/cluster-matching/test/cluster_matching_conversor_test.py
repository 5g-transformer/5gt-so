import json
import networkx as nx
import sys
sys.path.append('..')
sys.path.append('../src')
from graph_interactions import *


if __name__ == "__main__":
    scenario = json.load(open('example_scenario_with_decisions.json'))

    # Hosts graph
    hosts_graph = create_hosts_graph(scenario)
    nx.write_gml(hosts_graph, 'out/host.gml')

    # NS graph
    ns_graphs = create_ns_list(scenario)
    i = 0
    for ns_graph_ in ns_graphs:
        ns_graph = ns_graphs[ns_graph_]
        nx.write_gml(ns_graph, 'out/ns-' + str(ns_graph_) + '.gml')
        i += 1

    # Host clusters
    host_clusters = create_host_clusters(scenario)
    for host_cluster_no in host_clusters:
        host_cluster = host_clusters[host_cluster_no]
        nx.write_gml(host_cluster, 'out/host-cluster-' + str(host_cluster_no)\
            + '.gml')

    # VNF clusters
    vnf_clusters = create_vnf_clusters(scenario)
    for vnf_cluster_no in vnf_clusters:
        vnf_cluster = vnf_clusters[vnf_cluster_no]
        nx.write_gml(vnf_cluster, 'out/vnf-cluster-' + str(vnf_cluster_no) + \
            '.gml')

