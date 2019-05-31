import sys
sys.path.append('../src/')
from garrota import *

if __name__ == '__main__':
    capabilities = {
        'cpu': 10,
        'memory': 100,
        'disk': 1000
    }
    used_capabilities = {
        'cpu': 2,
        'memory': 80,
        'disk': 100
    }
    req_capabilities = {
        'cpu': 6,
        'memory': 0,
        'disk': 0
    }

    res_fullness = resources_fullness(capabilities, used_capabilities)
    if res_fullness['cpu'] == 0.2 and res_fullness['memory'] == 0.8\
        and res_fullness['disk'] == 0.1:
        print 'resources_fullness() OK'
    else:
        print 'resources_fullness() ERR -> maybe representation error\
 dont\'t worry'

    res_availability = resources_availability(capabilities, used_capabilities)
    if res_availability['cpu'] == 0.8 and res_availability['memory'] == 0.2\
        and res_availability['disk'] == 0.9:
        print 'resources_availability() OK'
    else:
        print 'resources_availability() ERR -> maybe representation issue,\
 don\'t worry'

    res_av_mean = resources_availability_mean(capabilities, used_capabilities)
    if abs(res_av_mean - 0.63) <= 0.05:
        print 'resources_availability_mean() OK'
    else:
        print 'resources_availability_mean() ERR -> maybe representation\
 issue, don\'t worry'

    res_unbalance = resources_unbalance(capabilities, used_capabilities)
    if abs(res_unbalance - 0.87) <= 0.05:
        print 'resources_unbalance() OK'
    else:
        print 'resources_unbalance() ERR -> maybe representation\
 issue, don\'t worry'
        
    map_un = map_unbalance(capabilities, used_capabilities,
        req_capabilities)
    if abs(map_un - 0.93) <= 0.05:
        print 'map_un() OK'
    else:
        print 'map_un() ERR -> maybe representation\
 issue, don\'t worry'





    # ==========================================
    # === TESTs RELATED TO MAPPING FUNCTIONS ===
    # ==========================================
    scenario = json.load(open('example_scenario_cluster_matching_test.json'))

    hosts = create_hosts_graph(scenario)
    hosts_clusters = create_host_clusters(scenario)
    vnf_clusters = create_vnf_clusters(scenario)
    host_cluster1 = hosts_clusters[1]
    host_cluster2 = hosts_clusters[2]
    vnf_cluster1 = vnf_clusters[1]
    vnf_cluster2 = vnf_clusters[2]

    if can_map_clusters(vnf_cluster1, host_cluster1):
        print 'can_map_cluster() OK'
    else:
        print 'can_map_cluster() ERR'

    if not can_map_clusters(vnf_cluster2, host_cluster2):
        print 'failing can_map_cluster() OK'
    else:
        print 'failing can_map_cluster() ERR'
    

    # ============================================
    # === TEST THE CLUSTER TO CLUSTER MATCHING ===
    # ============================================
    garrote_mapping(scenario)
