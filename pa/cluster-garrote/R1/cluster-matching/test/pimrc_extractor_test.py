import sys
imort json
sys.append('../src')

from pimrc_extractor import *

if __name__ == '__main__':
    scenario = json.load(open('example_scenario_with_decisions.json'))

    cap_h1 = host_capabilities(scenario, 'h1')
    if cap_h1['storage'] == 1000 and cap_h1['cpu'] == 16\
        and cap_h1['memory'] == 128:
        print 'host_capabilities() OK'
    else:
        print 'host_capabilities() ERR'

    rem_cap_h1 = remain_host_capabilities(scenario, 'h1')
    if rem_cap_h1['storage'] == 988.5 and rem_cap_h1['cpu'] == 16\
        and rem_cap_h1['memory'] == 121:
        print 'remain_host_capabilities() OK'
    else:
        print 'remain_host_capabilities() ERR'


    vnf_req = vnf_requirements(scenario, 'vnf1')
    if vnf_req['storage'] == 10 and vnf_req['cpu'] == 1\
        and vnf_req['memory'] == 4:
        print 'vnf_requirements() OK'
    else:
        print 'vnf_requirements() ERR'

    edge_cap = edge_capacity(scenario, 'h1', 'h2')
    if edge_cap == 1000:
        print 'edge_capacity() OK'
    else:
        print 'edge_capacity() ERR'

    edge_delay = edge_delay(scenario, 'h1', 'h2')
    if edge_delay == 0.001:
        print 'edge_delay() OK'
    else:
        print 'edge_delay() ERR'

    remain_edge_cap = remain_edge_capacity(scenario, '')


