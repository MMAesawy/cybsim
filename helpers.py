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


def get_subnetwork_device_count():
    return random.randint(4, 50)


def get_subnetwork_user_count(devices_count):
    return random.randint(2, devices_count - int(devices_count/2))


class AddressServer:
    """
        Controls and facilitates the conversion between a hierarchical address (e.g. 1.22.1.3)
        and a numerical serial address. Needed for Mesa's visualization engine
    """

    def __init__(self, initial=0):
        self.next_address = initial
        self.addresses = {}

    def __contains__(self, item):
        return item in self.addresses

    def __getitem__(self, address):
        if address not in self.addresses:
            self.addresses[address] = self.next_address
            self.next_address += 1
            return self.next_address - 1
        else:
            return self.addresses[address]

    def reverse_lookup(self, address):
        for k, v in self.addresses.items():
            if v == address:
                return k
        return None


class Packet:
    def __init__(self, packet_id, destination, payload, max_hops, stop_step=None, step=0):
        self.packet_id = packet_id
        self.destination = destination
        self.payload = payload
        self.max_hops = max_hops
        self.step = step
        self.stop_step = stop_step

class Address:
    def __init__(self, address):
        self.address = []

        # if the address is a string, parse the address into its components
        if isinstance(address, str):
            r = re.compile(r"(\d+)\s*([,.]|$)")
            for m in r.finditer(address):
                if m:
                    self.address.append(m.group(1))
        elif isinstance(address, int):
            self.address = [address]
        elif isinstance(address, list) or isinstance(address, tuple):
            # iterate to avoid tuple immutability, also as a way to copy
            for a in address:
                self.address.append(a)

    def is_share_subnetwork(self, other):
        i = 0
        while i < min(len(self), len(other)) and self[i] == other[i]:
            i += 1
        return i >= len(self) - 1

    def is_supernetwork(self, other):
        if len(self) > len(other):
            return False
        i = 0
        while i < min(len(self), len(other)) and self[i] == other[i]:
            i += 1
        return i == len(self)

    def __str__(self):
        return ".".join([str(a) for a in self.address])

    def __getitem__(self, item):
        return self.address[item]

    def __int__(self):
        return int("".join([str(a) for a in self.address]))

    def __len__(self):
        return len(self.address)

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        if self.n > len(self):
            raise StopIteration
        else:
            result = self[self.n]
            self.n += 1
            return result

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        for i in range(len(self)):
            if self[i] != other[i]:
                return False
        return True

    def __add__(self, other):
        if other is Address:
            return Address(self.address + other.address)
        elif isinstance(other, list) or isinstance(other, tuple):
            return Address(self.address + other)
        elif isinstance(other, int):
            return Address(self.address + [other])
        else:
            raise ValueError("Address addition error: 'other' is of invalid type: %s" % str(type(other)))

    def __setitem__(self, key, value):
        self.address[key] = value

    def __hash__(self):
        return hash(str(self))
