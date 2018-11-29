import sys
import copy
sys.path.append('../src/')
from garrota import *
from graph_interactions import *
import networkx as nx

if __name__ == '__main__':
    updated_scenario = json.load(open('updated_base_pimrc18_scenario.json'))
    hosts_g = create_hosts_graph(updated_scenario)
    nx.write_gml(hosts_g, "out/updated_base_pimrc18_scenario_hosts.gml")

    ns_graphs = create_ns_list(updated_scenario)
    i = 0
    for ns_graph in ns_graphs:
        nx.write_gml(ns_graphs[ns_graph], 'out/updated_base_pimrc18_scenario_ns' +\
            str(i) + '.gml')
        i += 1


    
