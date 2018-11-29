import sys
import copy
sys.path.append('../src/')
from garrota import *
from graph_interactions import *
import networkx as nx

if __name__ == '__main__':
    scenario = json.load(open('pimrc18_clustering_output.json'))
    hosts_g = create_hosts_graph(scenario)
    nx.write_gml(hosts_g, "out/base_pimrc18_scenario_hosts.gml")

    ns_graphs = create_ns_list(scenario)
    i = 0
    for ns_graph in ns_graphs:
        nx.write_gml(ns_graphs[ns_graph], 'out/base_pimrc18_scenario_ns' +\
            str(i) + '.gml')
        i += 1


    
