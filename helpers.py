import re
import networkx as nx
import random


def get_random_graph(num_nodes, avg_node_degree):
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


def get_subnetwork_device_count(model):
    return random.randint(model.min_device_count, model.max_device_count)


def get_subnetwork_user_count(devices_count):
    return random.randint(2, devices_count - int(devices_count/2))

def get_company_security(device_count): #TODO change security ranges to be realistic

    if 5 <= device_count <= 15:
        return random.random() * 0.25
    elif 16 <= device_count <= 25:
        return 0.25 + random.random() * (0.35 - 0.25)
    elif 26 <= device_count  <= 35:
        return 0.35 + random.random() * (0.5 - 0.35)
    elif 36 <= device_count  <= 50:
        return 0.85 + random.random() * (0.85 - 0.5)
    else:
        return 0.4 + random.random() * (0.6 - 0.4)

def get_subnetwork_attacker_count():
    return random.randint(2, 10)

