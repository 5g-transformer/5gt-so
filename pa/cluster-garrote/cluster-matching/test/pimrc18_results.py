import sys
import copy
sys.path.append('../src/')
from garrota import *
import time

if __name__ == '__main__':

    # Print ns graphs
    clustering = json.load(open('pimrc18_clustering_output.json'))
    ns_graphs = create_ns_list(clustering)
    for ns_name in ns_graphs:
        nx.write_gml(ns_graphs[ns_name], "/tmp/ns_old_" + ns_name + ".gml")


    # Create an scenario per clustering decision
    clustering = json.load(open('pimrc18_clustering_output.json'))
    for decision in clustering['clustering_decisions']:
        scenario = copy.deepcopy(clustering)
        print '=> #clusters = ' + str(decision['no_clusters'])

        # Put cluster decisions in original PIMRC18 format
        for as_vnf_name in decision['assignment_vnfs']:
            as_vnf_cl = decision['assignment_vnfs'][as_vnf_name]
            for i in range(len(scenario['vnfs'])):
                vnf_name = scenario['vnfs'][i]['vnf_name']
                if vnf_name == as_vnf_name:
                    scenario['vnfs'][i]['cluster'] = as_vnf_cl

        # Put cluster decisions in original PIMRC18 format
        for as_host_name in decision['assignment_hosts']:
            as_host_cl = decision['assignment_hosts'][as_host_name]
            for i in range(len(scenario['hosts'])):
                host_name = scenario['hosts'][i]['host_name']
                if host_name == as_host_name:
                    scenario['hosts'][i]['cluster'] = as_host_cl
                    
                    import time

        # Print in a JSON
        start_time = time.time()
        scenario, worked = garrote_mapping(scenario)
        scenario['execution_time'] = "%s" % (time.time() - start_time)
        if worked:
            mapping_costs(scenario)
            mapped_ns_delays(scenario)
            with open('pimrc18_results/cluster_matching_' +\
                str(decision['no_clusters']) + '.json', 'w') as fp:
                json.dump(scenario, fp, indent=4)
