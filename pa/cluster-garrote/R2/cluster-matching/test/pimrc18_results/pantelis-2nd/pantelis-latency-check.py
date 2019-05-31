import sys
import copy
sys.path.append('../../../src')
sys.path.append('../../../../generator/src/vnfsMapping')

from garrota import *
import time

if __name__ == '__main__':

    # Print ns graphs
    scenario = json.load(open('solution-latency-X.json'))

    for vnf in scenario['vnfs']:
        for ser in vnf['place_at']:
            i = 0
            for i in range(len(scenario['hosts'])):
                if scenario['hosts'][i]['host_name'] == ser:
                    if not 'mapped_vnfs' in scenario['hosts'][i]:
                        scenario['hosts'][i]['mapped_vnfs'] = []
                    scenario['hosts'][i]['mapped_vnfs'].append(vnf['vnf_name'])

    print 'mapped delays GA_latency: ' + str(mapped_ns_delays(scenario))
