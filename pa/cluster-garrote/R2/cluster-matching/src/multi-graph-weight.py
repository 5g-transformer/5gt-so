import networkx as nx

if __name__ == '__main__':
    ns = nx.MultiGraph()
    ns.add_node("v1")
    ns.add_node("v2")
    ns.add_node("v3")
    ns.add_node("v4")
    ns.add_edge("v1", "v2", bandwidth=10)
    ns.add_edge("v1", "v2", bandwidth=30)
    ns.add_edge("v2", "v3", bandwidth=20)
    ns.add_edge("v3", "v4", bandwidth=10)
    ns.add_edge("v1", "v4", bandwidth=5)

    nfvis = nx.MultiGraph()
    nfvis.add_node("A")
    nfvis.add_node("B")
    nfvis.add_node("C")
    nfvis.add_node("D")
    nfvis.add_node("E")
    nfvis.add_edge("A", "B", bandwidth=20)
    nfvis.add_edge("A", "C", bandwidth=40)
    nfvis.add_edge("A", "F", bandwidth=30)
    nfvis.add_edge("B", "F", bandwidth=15)
    nfvis.add_edge("C", "F", bandwidth=35)
    nfvis.add_edge("C", "D", bandwidth=16)
    nfvis.add_edge("F", "E", bandwidth=20)
    nfvis.add_edge("F", "E", bandwidth=20)

    for vl in nx.get_edge_attributes(ns, 'bandwidth'):
        print "At VL " + str(vl)
        vlBw = ns[vl[0]][vl[1]][vl[2]]['bandwidth']

        # New nfviPoP graph and remove BW LLs < VLs
        nfvisCp = nfvis.copy()
        for ll in nx.get_edge_attributes(nfvisCp, "bandwidth"):
            llBw = nfvisCp[ll[0]][ll[1]][ll[2]]['bandwidth']
            if llBw < vlBw:
                nfvisCp.remove_edge(ll[0], ll[1], ll[2])

        pred, dist = nx.bellman_ford(nfvisCp, "A", weight = 'bandwidth')
        print "pred:" + str(pred)
        print "dist:" + str(dist)

        
        break


    


