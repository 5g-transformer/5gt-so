def host_capabilities(scenario, host_name):
    """Extracts the host capabilitiesfrom the PIMRC18 scenario.

    :scenario: PIMRC18 scenario JSON
    :host_name: unique host name in the scenario
    :returns: dictionary with the PIMRC18 capabilities

    """
    found = False
    i = 0
    while not found and i < len(scenario['hosts']):
        found = scenario['hosts'][i] == host_name
        if not found:
            i += 1

    return {} if not found else scenario['hosts'][i]['capabilities']


def remain_host_capabilities(scenario, host_name):
    """Extracts the remaining host capabilities

    :scenario: PIMRC18 scenario JSON
    :host_name: unique host name in the scenario
    :returns: dictionary with the PIMRC18 capabilities

    """
    remain_capab = host_capabilities(scenario, host_name)
    
    for vnf in scenario['vnfs']:
        if host_name in vnf['place_at']:
            for capability in remain_capab:
                remain_capab['capability'][capability] -=\
                    vnf['requirements'][capability]

    return remain_capab


def vnf_requirements(scenario, vnf_name):
    """Extracts the VNF requirements from the PIMRC18 scenario.

    :scenario: PIMRC18 scenario JSON
    :vnf_name: unique VNF name in the scenario
    :returns: dictionary with the PIMRC18 requirements of the VNF

    """
    found = False
    i = 0
    while not found and i < len(scenario['vnfs']):
        found = vnf_name in scenario['vnfs'][i]['vnf_name']
        if not found:
            i += 1

    return scenario['vnfs'][i]['requirements']


def edge_delay(scenario, host1_name, host2_name):
    """Extracts the traffic delay of a host edge

    :scenario: PIMRC18 scenario JSON
    :host1_name: unique host1 name in the scenario
    :host2_name: unique host2 name in the scenario
    :returns: the host edge traffic delay, None if ther is not such edge

    """
    i = 0
    traffic_delay = None
    found = False
    while not found and i < len(scenario['host_edges']):
        src = scenario['host_edges'][i]['source']
        dst = scenario['host_edges'][i]['target']
        found = (host1_name == src or host1_name == dst)\
                and (host2_name == src or host2_name == dst)

        if not found:
            i += 1
        else:
            traffic_delay = scenario['host_edges'][i]['delay']

    return traffic_delay


def edge_capacity(scenario, host1_name, host2_name):
    """Extracts the traffic capacity of a host edge from host1_name to
    host2_name

    :scenario: PIMRC18 scenario JSON
    :host1_name: unique host1 name in the scenario
    :host2_name: unique host2 name in the scenario
    :returns: the host edge traffic capacity, None if ther is not such edge

    """
    i = 0
    traffic_capacity = None
    found = False
    while not found and i < len(scenario['host_edges']):
        src = scenario['host_edges'][i]['source']
        dst = scenario['host_edges'][i]['target']
        found = (host1_name == src or host1_name == dst)\
                and (host2_name == src or host2_name == dst)

        if not found:
            i += 1
        else:
            traffic_capacity = scenario['host_edges'][i]['capacity']


    return traffic_capacity


def remain_edge_capacity(scenario, host1_name, host2_name):
    """Extracts the remaining traffic capacity of a host edge

    :scenario: PIMRC18 scenario JSON
    :host1_name: unique host1 name in the scenario
    :host2_name: unique host2 name in the scenario
    :returns: the remaining host edge traffic capacity, None if ther is not
    such edge

    """
    edge_cap = edge_capacity(scenario, host1_name, host2_name)
    if edge_cap == None:
        return None

    for vnf_edge in scenario['vnf_edges']:
        for placed_edge in vnf_edge['place_at']:
            src = placed_edge['source']
            dst = placed_edge['target']
            found = (host1_name == src or host1_name == dst)\
                    and (host2_name == src or host2_name == dst)
            if found:
                edge_cap -= vnf_edge['traffic']

    return edge_cap

