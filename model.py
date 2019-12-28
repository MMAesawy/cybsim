from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import networkx as nx
import random
import re
import numpy as np

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


class AddressServer:
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



class CybCim(Model):

    def __init__(self):
        super().__init__()

        self.G = nx.Graph()
        self.address_server = AddressServer()

        self.num_internet_devices = 100
        self.num_subnetworks = 15
        #avg_node_degree = 3

        self.network = get_random_graph(self.num_subnetworks, 2)
        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.network))

        self.packet_payloads = ["Just passing through!", "IDK anymore...", "Going with the flow!", "Leading the way.",
                                "Taking the high road!", "I'm on the hiiiiiighway to hell!", "gg ez",
                                "I want to go home ):", "It's funny how, in this journey of life, even though we may "
                                                        "begin at different times and places, our paths cross with "
                                                        "others so that we may share our love, compassion, observations"
                                                        ", and hope. This is a design of God that I appreciate and "
                                                        "cherish.",
                                "It's all ogre now.", "I need to go", "Seeing is believing!", "I've been on these roads"
                                                                                              " for as long as i can "
                                                                                              "remember..."]

        self.devices = []
        for i, n in enumerate(self.network.nodes):
            routing_table = self.shortest_paths[n]
            if n == self.network.graph['gateway']:
                a = SubNetwork(Address(self.network.graph['gateway']), self, self,
                               routing_table, of='devices',
                               num_devices=self.num_internet_devices,
                               avg_node_degree=1)
            else:
                a = SubNetwork(Address(i), self, self,
                           routing_table,
                               avg_node_degree=1,
                            of = 'devices'
                           )
            self.network.nodes[n]['subnetwork'] = a
            # self.devices.append(a.gateway())
            # self.grid.place_agent(a, node)
            # self.schedule.add(a)

        for s, d in self.network.edges:
            ns = self.network.nodes[s]['subnetwork'].gateway()
            nd = self.network.nodes[d]['subnetwork'].gateway()
            ns_address = self.address_server[ns.address]
            nd_address = self.address_server[nd.address]
            if not self.G.get_edge_data(ns_address, nd_address)\
                and not self.G.get_edge_data(nd_address, ns_address):
                self.G.add_edge(ns_address, nd_address)

        # print([len(x) for x in self.shortest_paths.values()])
        for edge in self.G.edges(data=True):
            edge[2]["active"] = False
        self.grid = NetworkGrid(self.G)
        self.schedule = RandomActivation(self)
        for d in self.devices:
            self.grid.place_agent(d, self.address_server[d.address])
            self.schedule.add(d)
        self.total_packets_received = 0
        self.packet_count = 1

        self.datacollector = DataCollector(
            {"packets_received": "total_packets_received"},
        )

        self.running = True
        self.datacollector.collect(self)
        print("Starting!")
        # print(len(self.devices))
        # print(self.G.nodes)
        # print(EDGES)
        # print(len(self.G.edges))


    def step(self):
        # deactivate all edges
        for edge in self.G.edges(data=True):
            edge[2]["active"] = False
        # update agents
        self.schedule.step()

class SubNetwork(Agent):
    def __init__(self, address, parent, model, routing_table, of='subnetworks', num_devices=25, avg_node_degree=2):
        super().__init__(address, model)


        self.address = address
        self.parent = parent
        self.routing_table = routing_table
        self.of = of

        self.num_devices = num_devices

        self.network = get_random_graph(self.num_devices, avg_node_degree)
        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.network))

        for i, n in enumerate(self.network.nodes):
            routing_table = self.shortest_paths[n]
            if of == 'subnetworks':
                self.network.nodes[n]['subnetwork'] = SubNetwork(self.address + i, self, model, routing_table,
                                                                 of='devices',
                                                                 num_devices=get_subnetwork_device_count())
            elif of == 'devices':
                self.network.nodes[n]['subnetwork'] = NetworkDevice(self.address + i, self, model, routing_table)

        for s, d in self.network.edges:
            ns = self.network.nodes[s]['subnetwork'].gateway()
            nd = self.network.nodes[d]['subnetwork'].gateway()
            ns_address = model.address_server[ns.address]
            nd_address = model.address_server[nd.address]
            if not model.G.get_edge_data(ns_address, nd_address):
                model.G.add_edge(ns_address, nd_address)


    def route(self, packet):
        # if destination is inside this network
        if self.address.is_supernetwork(packet.destination):
            next_device = self.gateway()
        # if destination is in this network's subnetwork
        elif self.address.is_share_subnetwork(packet.destination):  # device is in the local network
            next_device_address = self.routing_table[packet.destination[len(self.address) - 1]][1]
            next_device = self.parent.network.nodes[next_device_address]['subnetwork']
        else:  # device is outside the local network, send to gateway:
            # if this is the gateway device:
            if self.address[-1] == self.parent.network.graph['gateway']:
                next_device = self.parent
            else:  # this is not the gateway device:
                next_device_address = self.routing_table[self.parent.gateway().address[len(self.address) - 1]][1]
                next_device = self.parent.network.nodes[next_device_address]['subnetwork']

        # print(self.routing_table)
        # if packet.destination not in self.routing_table:
        #     print("Cannot connect to %d, packet discarded." % packet.destination)
        #     self.model.packet_count = self.model.packet_count - 1
        #     return



        print("Subnetwork %s sending packet %s to device %s" % (self.address, packet.destination, next_device.address))
        # only color edge if not sending packet "upwards"
        if len(self.address) == len(next_device.address):
            self.model.G.get_edge_data(self.model.address_server[self.gateway().address],
                                       self.model.address_server[next_device.gateway().address])[
                "active"] = True
        next_device.route(packet)

    def step(self):
        for n in self.network.nodes:
            n['subnetwork'].step()

    def gateway(self):
        return self.network.nodes[self.network.graph['gateway']]['subnetwork'].gateway()


class NetworkDevice(Agent):

    def __init__(self, address, parent, model, routing_table):
        self.address = address
        self.model_address = model.address_server[self.address]
        super().__init__(address, model)

        self.parent = parent
        self.routing_table = routing_table
        self.packets_received = 0
        self.packets_sent = 0
        self.occupying_packets = []
        model.devices.append(self)

        if self.model_address not in model.G.nodes:
            model.G.add_node(self.model_address)

    def route(self, packet):
        if self.address == packet.destination:
            self.packets_received += 1
            self.occupying_packets.append(packet)
            self.model.total_packets_received += 1
            print("Device %s received packet: %s" % (self.address, packet.payload))
            return
        elif self.address.is_share_subnetwork(packet.destination): # device is in the local network
            next_device_address = self.routing_table[packet.destination[len(self.address) - 1]][1]
            next_device = self.parent.network.nodes[next_device_address]['subnetwork']
        else: # device is outside the local network, send to gateway:
            # if this is the gateway device:
            if self is self.parent.gateway():
                next_device = self.parent
            else: # this is not the gateway device:
                next_device_address = self.routing_table[self.parent.gateway().address[len(self.address) - 1]][1]
                next_device = self.parent.network.nodes[next_device_address]['subnetwork']


        # print(self.routing_table)
        # if packet.destination not in self.routing_table:
        #     print("Cannot connect to %d, packet discarded." % packet.destination)
        #     self.model.packet_count = self.model.packet_count - 1
        #     return



        print("Device %s sending packet %s to device %s" % (self.address, packet.destination, next_device.address))

        self.packets_sent += 1
        # only color edge if not sending packet "upwards"
        if len(self.address) == len(next_device.address):
            self.model.G.get_edge_data(self.model.address_server[self.address], self.model.address_server[next_device.address])["active"] = True
        next_device.route(packet)

    def gateway(self):
        return self


    def step(self):
        r = random.random()
        # print(r)
        if r < 0.001:
            dest = random.choice(self.model.devices).address
            packet = Packet(self.model.packet_count, dest, random.choice(self.model.packet_payloads))
            self.model.packet_count = self.model.packet_count + 1
            print("Device %s attempting to message %s" % (self.address, dest))
            self.route(packet)


class Packet:
    def __init__(self, packet_id, destination, payload):
        self.packet_id = packet_id
        self.destination = destination
        self.payload = payload

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
