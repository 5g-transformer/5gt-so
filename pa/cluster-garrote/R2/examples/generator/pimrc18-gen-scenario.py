import sys
sys.path.append('../../generator/src/vnfsMapping/')
from AbsFatTreeGen import *
from NsGenerator import *
import json

if __name__ == '__main__':
    k = 4
    # Data-center properties
    linkProps = {
        'delay': 1,
        'capacity': 1000
    }
    serverProps = {
        "capabilities": {
            "storage": 1000, 
            "cpu": 16, 
            "memory": 128
        }
    }
    # NS properties
    linkTh = {
        'traffic': {'min': 1, 'max': 4},
        'delay': {'min': 1, 'max': 4}
    }
    vnfTh = {
        "processing_time": {'min': 1, 'max': 4},
        "requirements": {
            "storage": {'min': 1, 'max': 4}, 
            "cpu": {'min': 1, 'max': 4}, 
            "memory": {'min': 1, 'max': 4}
        }
    }

    # Create a NET abstraction fat-tree
    fat_tree_gen = AbsFatTreeGen()
    NET_fat_tree = fat_tree_gen.yieldFatTree(k, linkProps, serverProps,
        abstraction='NET')

    # Create a list of NSs
    ns_gen = NSgenerator(linkTh, vnfTh)
    nss = [ns_gen.yieldChain(splits=3, splitWidth=3, branches=3, vnfs=6)
        for _ in range(20)]

    # Put everything inside the PIMRC18 JSON
    pimrc = AbsFatTreeGen.NETtoPimrc(NET_fat_tree, linkProps, serverProps)
    for ns in nss:
        pimrc = ns.toPimrc(pimrc)

    with open('out/pimrc18-gen-scenario.json', 'w') as outfile:
        json.dump(pimrc, outfile)

