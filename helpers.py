import networkx as nx
import numpy as np
import globalVariables



def random_string(length = 8):
    return "".join([chr(globalVariables.RNG.randint(ord("a"), ord("z"))) for _ in range(length)])


def random_star_graph(num_nodes, avg_node_degree):
    # calculate single edge probability between two nodes
    prob = avg_node_degree / num_nodes

    # initialize star graph to ensure graph connectivity, specify the hub as the gateway
    graph = nx.Graph()
    for i in range(num_nodes):
        graph.add_node(i)
    graph.graph['gateway'] = globalVariables.RNG.choice(range(num_nodes)) # select a random node as the gateway
    # connect all nodes to the gateway
    for i in range(num_nodes):
        if i != graph.graph['gateway']:
            graph.add_edge(graph.graph['gateway'], i)

    # loop over every pair of nodes
    for i in range(0, num_nodes):
        for j in range(i+1, num_nodes):
            # if edge does not already exist and edge creation success, create edge.
            if j not in graph[i] and globalVariables.RNG.random() < prob:
                graph.add_edge(i, j)
            else:
                globalVariables.RNG.random()  # dummy, for consistent randomness during branching

    # the returned graph will be fully connected with a "gateway" hub node,
    # and some random connections between the other nodes.
    return graph


def random_mesh_graph(num_nodes, m=3):
    g = nx.barabasi_albert_graph(num_nodes, m)
    g.graph['gateway'] = globalVariables.RNG.randint(0, num_nodes-1) # pick a random node as the gateway
    return g


def get_subnetwork_device_count(model):
    return model.device_count
    # return random.randint(model.min_device_count, model.max_device_count)


def get_subnetwork_user_count(devices_count):
    return globalVariables.RNG.randint(2, devices_count - int(devices_count/2))

# def get_subnetwork_attacker_count():
#     return random.randint(2, 10)

def get_prob_detection(defense, attack):
    return defense / (defense + attack + 1e-5)

def get_prob_detection_v2(security, attack, information, info_weight=2):
    return security / (security + info_weight * (1-information) * attack + 0.1)

def get_prob_detection_v3(aggregate_security, attack, stability=1e-3):
    return aggregate_security / (aggregate_security + attack + stability)

def get_defense(total_security, information, information_weight=1):
    x = 1 - total_security
    y = 1 - information
    b = information_weight
    return (2 - x**0.5 * y**(0.5*b) - x * y**b) / 2

def get_new_information_selfish(i1, i2):
    return np.logical_or(i1, i2)
   # return i1+i2*(1-i1)

def get_new_information_cooperative(i1, i2):
    # i2 > i1
    return np.logical_or(i1, i2)
    # return i1 + ((i2 - i1) / sp) # TODO remove SP
    # return max(i1, i2)

def get_reciprocity(choice, c, r):
    # TODO: don't use magic numbers
    if choice == 2:
        return 1 - ((1 - c) / r)
    elif choice == 0:
        return c / r


def increase_trust(ct, tf):
    """ ct: the current trust between the two organizations
        tf: the trust factor
    """
    # TODO possibly change function to show certain behaviour
    return 1 - ((1 - ct) / tf)

def decrease_trust(ct, tf):
    """ ct: the current trust between the two organizations
        tf: the trust factor
    """
    return ct / tf

def get_new_information_detected(probability, old_information, w = 0.5):
    x = old_information
    y = probability
    return min(1.0, x + y**2 * (1-x)*w)

def get_total_security(security_budget, deviation_width):
    return min(1, max(0, globalVariables.RNG.normal(security_budget, deviation_width/6)))

def share_info_selfish(org1, org2): #org1 only shares
    old_info_o1 = org1.old_attacks_list
    old_info_o2 = org2.old_attacks_list
    new_info = np.logical_or(old_info_o1, old_info_o2)

    o = old_info_o1.mean(axis=1).sum()
    org2.info_in += o
    org1.info_out += o
    org1.org_out[org2.id] += o
    org2.new_attacks_list = np.logical_or(new_info, org2.new_attacks_list)


def share_info_cooperative(org1, org2): #org1 shares with org2
    old_info_o1 = org1.old_attacks_list
    old_info_o2 = org2.old_attacks_list
    new_info = np.logical_or(old_info_o1, old_info_o2)

    org2.info_in += np.logical_xor(new_info, old_info_o2).mean(axis=1).sum()
    o = np.logical_xor(new_info, old_info_o1).mean(axis=1).sum()
    org1.info_out += o
    org1.org_out[org2.id] += o
    org2.new_attacks_list = np.logical_or(new_info, org2.new_attacks_list)

def free_loading_ratio_v1(info_in, info_out):
    return info_in / (info_in + info_out + 1e-5)


