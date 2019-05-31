import sys
import json
sys.path.append('../../src')
from garrota import *

if __name__ == '__main__':
    pa_req = None
    ch_pa_req = None
    worked = None
    
    with open('test_req_cluster_decisions.json') as f:
        pa_req = json.load(f)

    ch_pa_req = best_garrote(pa_req)
    with open('/tmp/test_release1_result.json', 'w') as f:
        json.dump(ch_pa_req, f, indent = 4)

