import sys
import json
sys.path.append('../src')
from graph_interactions import *

if __name__ == '__main__':
    scenario = json.load(open('example_scenario_cluster_matching_test.json'))

    hosts = create_hosts_graph(scenario)
    hosts_clusters = create_host_clusters(scenario)
    vnf_clusters = create_vnf_clusters(scenario)
    host_cluster1 = hosts_clusters[1]
    host_cluster2 = hosts_clusters[2]
    vnf_cluster1 = vnf_clusters[1]
    vnf_cluster2 = vnf_clusters[2]

    # Exist link test
    exists, _ = exist_capable_edge(host_cluster2,
        vnf_cluster2, ('vnf4', 'vnf5'))
    if not exists:
        print 'OK: no link in hc2 to host v4-v5 edge'
    else:
        print 'ERR: there is no edge to map v4-v5 on hc2'

    exists, _ = exist_capable_edge(host_cluster1,
        vnf_cluster1, ('vnf1', 'vnf2'))
    if exists:
        print 'OK: exist link in hc1 to host v1-v2 edge'
    else:
        print 'ERR: there is a link in hc1 to host v1-v2 edge'

    # Exist host test
    vnf1 = get_vnf(vnf_cluster1, 'vnf1')
    vnf4 = get_vnf(vnf_cluster2, 'vnf4')
    exists, _ = exist_capable_host(vnf4, host_cluster2)
    if not exists:
        print 'OK: no capable host in cluster2 for vnf4'
    else:
        print 'ERR: no capable host in cluster2 for vnf4'

    exists, _ = exist_capable_host(vnf1, host_cluster1)
    if exists:
       print 'OK: host in cluster1 capable of hosting vnf1'
    else:
       print 'ERR: host in cluster1 capable of hosting vnf1'


    # Enough cluster resources test
    if enough_cluster_res(vnf_cluster1, host_cluster1):
        print 'OK: hosts cluster1 has resources for vnf_cluster1'
    else:
        print 'ERR: hosts cluster1 has resources for vnf_cluster1'
    if enough_cluster_res(vnf_cluster2, host_cluster2):
        print 'OK: hosts cluster2 has not resources for vnf_cluster2'
    else:
        print 'OK: hosts cluster2 has not resources for vnf_cluster2'


    # Test cluster overall capabilites reduction
    h1_cap = hosts_cluster_free_cap(host_cluster1)
    cap_red = {
        'host': {
            'cpu': 20,
            'memory': 200,
            'storage': 200000000
        },
        'link': {
            'capacity': 10
        }
    }
    fake_cluster_cap_reduction(host_cluster1, cap_red)
    h1_cap_red = hosts_cluster_free_cap(host_cluster1)
    all_ok = True
    for capability in h1_cap:
        all_ok = all_ok and\
            h1_cap_red[capability] ==\
                h1_cap[capability] - cap_red['host'][capability]

    if all_ok:
        print 'OK: cluster fake capabilities reduction'
    else:
        print 'ERR: cluster fake capabilities reduction'
    for cap in cap_red['host']:
        cap_red['host'][cap] = -1 * cap_red['host'][cap]
    for cap in cap_red['link']:
        cap_red['link'][cap] = -1 * cap_red['link'][cap]
    fake_cluster_cap_reduction(host_cluster1, cap_red)


    # Cluster matching cost test
    match_cost = cluster_match_cost(vnf_cluster1, host_cluster1)
    if match_cost == 4.5:
        print 'OK: ns cluster matching cost'
    else:
        print 'ERR: ns cluster maching cost'


    # Cluster resources capabilities
    cluster_cap = hosts_cluster_cap(host_cluster1)
    if cluster_cap['cpu'] == 32 and cluster_cap['storage'] == 2000\
        and cluster_cap['memory'] == 256:
        print 'OK: host cluster capabilities'
    else:
        print 'ERR: host cluster capabilities'

