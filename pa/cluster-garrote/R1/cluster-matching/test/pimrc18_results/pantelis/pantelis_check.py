import sys
import copy
sys.path.append('../../../src/')
sys.path.append('../../../../generator/src/vnfsMapping/')
from garrota import *
from NS import *

def to_mapped_vnf_edges(scenario):
    """Moves Pantelis vnf edge placement to host edges

    :scenario: PIMRC18 model JSON
    :returns: updated scenario

    """
    for vnf in scenario['vnfs']:
        vnf['cluster'] = 'undefined'

    for hosts_edge in scenario['host_edges']:
        h_src = hosts_edge['source']
        h_dst = hosts_edge['target']
        hosts_edge['mapped_vnf_edges'] = []
        for vnfs_edge in scenario['vnf_edges']:
            if 'host_edge' in vnfs_edge:
                v_src = vnfs_edge['host_edge']['source']
                v_dst = vnfs_edge['host_edge']['target']

                if v_src == h_src and v_dst == h_dst:
                    hosts_edge['mapped_vnf_edges'].append({
                        "src": vnfs_edge["source"],
                        "target": vnfs_edge["target"]
                    })

    return scenario

if __name__ == '__main__':
    scenario_cost = json.load(open('solution-cost-X.json'))
    scenario_cost = to_mapped_vnf_edges(scenario_cost)

    mapped_ns_delays(scenario_cost)
    print '==== SOLUTION COST ===='
    for service in scenario_cost['services']:
        print service['service_name'] + ' mapped delay: ' +\
            str(service['mapped_delay'])
    print 'AVG delay: ' + str(scenario_cost['avg_services_delay'])

    scenario_latency = json.load(open('solution-latency-X.json'))
    scenario_latency = to_mapped_vnf_edges(scenario_latency)
    with open('/tmp/a-latency.json', 'w') as fp:
        json.dump(scenario_latency, fp, indent=4)
    mapped_ns_delays(scenario_latency)
    print '==== SOLUTION LATENCY ===='
    for service in scenario_latency['services']:
        print service['service_name'] + ' mapped delay: ' +\
            str(service['mapped_delay'])
    print 'AVG delay: ' + str(scenario_latency['avg_services_delay'])
