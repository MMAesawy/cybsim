import re
import networkx as nx
import random

def random_string(length = 8):
    return "".join([chr(random.randint(ord("a"), ord("z"))) for _ in range(length)])


def random_star_graph(num_nodes, avg_node_degree):
    # calculate single edge probability between two nodes
    prob = avg_node_degree / num_nodes

    # initialize star graph to ensure graph connectivity, specify the hub as the gateway
    graph = nx.Graph()
    for i in range(num_nodes):
        graph.add_node(i)
    graph.graph['gateway'] = random.choice(range(num_nodes)) # select a random node as the gateway
    # connect all nodes to the gateway
    for i in range(num_nodes):
        if i != graph.graph['gateway']:
            graph.add_edge(graph.graph['gateway'], i)

    # loop over every pair of nodes
    for i in range(0, num_nodes):
        for j in range(i+1, num_nodes):
            # if edge does not already exist and edge creation success, create edge.
            if j not in graph[i] and random.random() < prob:
                graph.add_edge(i, j)

    # the returned graph will be fully connected with a "gateway" hub node,
    # and some random connections between the other nodes.
    return graph


def random_mesh_graph(num_nodes, m=3):
    g = nx.barabasi_albert_graph(num_nodes, m)
    g.graph['gateway'] = random.randint(0, num_nodes-1) # pick a random node as the gateway
    return g


def get_subnetwork_device_count(model):
    return model.device_count
    # return random.randint(model.min_device_count, model.max_device_count)


def get_subnetwork_user_count(devices_count):
    return random.randint(2, devices_count - int(devices_count/2))

# def get_subnetwork_attacker_count():
#     return random.randint(2, 10)

def get_prob_detection(defense, attack):
    return defense / (defense + attack + 1e-5)

def get_prob_detection_v2(security, attack, information, info_weight=2):
    return security / (security + info_weight * (1-information) * attack + 0.1)

def get_defense(total_security, information, information_weight=1):
    x = 1 - total_security
    y = 1 - information
    b = information_weight
    return (2 - x**0.5 * y**(0.5*b) - x * y**b) / 2

def get_new_information_selfish(i1, i2):
    return i1+i2*(1-i1)

def get_new_information_cooperative(i1, i2, sp):
    # i2 > i1
    return i1 + ((i2 - i1) / sp)
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
    return min(1, max(0, random.gauss(security_budget, deviation_width/6)))

def share_info_selfish(org1, org2):
    for attack, info in org1.old_attacks_list.items():
        org2.new_attacks_list[attack] = get_new_information_selfish(org2.old_attacks_list[attack], info)

def share_info_cooperative(org1, org2, sp):
    for attack, info in org1.old_attacks_list.items():
        if info > org2.old_attacks_list[attack]:
            org2.new_attacks_list[attack] = get_new_information_cooperative(org2.old_attacks_list[attack], info, sp)

def adjust_transitivity(model, org1, org2):
    for i in range(model.num_subnetworks - 1):
        if i == org1 or i == org2:
            continue
        else:
            if abs(0.5 - model.closeness_matrix[org1][i]) > abs(0.5 - model.closeness_matrix[org2][i]):
                # if org1's opinion is more "extreme" than org2
                model.closeness_matrix[org2][i] /= model.transitivity
            else:
                # otherwise
                model.closeness_matrix[org1][i] /= model.transitivity

