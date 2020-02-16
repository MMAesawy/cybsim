import re
import networkx as nx
import random


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
    return random.randint(model.min_device_count, model.max_device_count)


def get_subnetwork_user_count(devices_count):
    return random.randint(2, devices_count - int(devices_count/2))

