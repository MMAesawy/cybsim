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

def get_subnetwork_user_count(devices_count):
    return random.randint(2, devices_count - int(devices_count/2))

'''
    Controls and facilitates the conversion between a hierarchical address (e.g. 1.22.1.3) 
    and a numerical serial address. Needed for Mesa's visualization engine
'''
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

        self.G = nx.Graph() # master graph
        self.address_server = AddressServer()

        self.num_internet_devices = 100
        self.num_subnetworks = 15
        #avg_node_degree = 3
        self.devices = []

        # create graph and compute pairwise shortest paths
        self.network = get_random_graph(self.num_subnetworks, avg_node_degree=2)
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



        # construct subnetworks that compose the main network
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]
            if i == self.network.graph['gateway']:
                n = self.num_internet_devices
            else:
                n = get_subnetwork_device_count()

            self.network.nodes[i]['subnetwork']  =  SubNetwork(address=Address(i),
                                                               parent=self,
                                                               model=self,
                                                               routing_table=routing_table,
                                                               avg_node_degree=1,
                                                               num_devices=n,
                                                               of='devices'
                                                 )


        # add nodes to master graph
        self.merge_with_master_graph()

        # initialize edge 'active' attribute
        for edge in self.G.edges(data=True):
            edge[2]["active"] = False

        # initialize agents
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

    def get_subnetwork_at(self, at):
        return self.network.nodes[at]['subnetwork']

    def step(self):
        # deactivate all edges
        for edge in self.G.edges(data=True):
            edge[2]["active"] = False
        # update agents
        self.schedule.step()

    '''
        Merges the abstract hierarchical graph with the 'master graph' for visualization purposes.
    '''
    def merge_with_master_graph(self):
        # add nodes to master graph
        for s, d in self.network.edges:
            ns = self.get_subnetwork_at(s).gateway_device()
            nd = self.get_subnetwork_at(d).gateway_device()
            ns_address = self.address_server[ns.address]  # creates address entry if it does not exist
            nd_address = self.address_server[nd.address]  # creates address entry if it does not exist
            if not self.G.get_edge_data(ns_address, nd_address):
                self.G.add_edge(ns_address, nd_address)

class SubNetwork:
    def __init__(self, address, parent, model, routing_table, of='subnetworks', num_devices=25, avg_node_degree=2):
        self.address = address
        self.parent = parent
        self.model = model
        self.routing_table = routing_table
        self.of = of
        self.num_devices = num_devices

        # create graph and compute pairwise shortest paths
        self.network = get_random_graph(self.num_devices, avg_node_degree)
        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.network))

        self.local_gateway_address = self.network.graph['gateway']

        self.children = []
        # create objects to be stored within the graph
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]
            if of == 'subnetworks': # if this is a subnetwork of subnetworks:
                self.network.nodes[i]['subnetwork'] = SubNetwork(address=self.address + i,
                                                                 parent=self,
                                                                 model=model,
                                                                 routing_table=routing_table,
                                                                 of='devices',
                                                                 num_devices=get_subnetwork_device_count())
            elif of == 'devices': # if this is a subnetwork of devices
                self.num_users = get_subnetwork_user_count(self.num_devices)
                if (i <= self.num_users):
                    active = random.random()
                    self.network.nodes[i]['subnetwork'] = User(active, address=self.address + i,
                                                                    parent=self,
                                                                    model=model,
                                                                    routing_table=routing_table)
                else:
                    self.network.nodes[i]['subnetwork'] = NetworkDevice(address=self.address + i,
                                                                    parent=self,
                                                                    model=model,
                                                                    routing_table=routing_table)
                self.children.append(self.network.nodes[i]['subnetwork'])

        # add nodes to master graph
        self.merge_with_master_graph()

    def route(self, packet):
        # if destination is inside this network, consume the packet (progagate downwards)
        if self.address.is_supernetwork(packet.destination):
            self._propagate_downwards(packet)
        else:
            self._send(packet)

    '''
        Logic for 'receiving' and propagating a network packet downwards.
    '''
    def _propagate_downwards(self, packet):
        self.gateway_device().route(packet)

    '''
        Logic for sending a network packet.
    '''

    def _send(self, packet):
        if self.address.is_share_subnetwork(packet.destination): # device is in the local network
            dest_local_address = packet.destination[len(self.address) - 1]
            next_device_address = self.routing_table[dest_local_address][1]
            next_device = self.parent.get_subnetwork_at(next_device_address)
        else:  # device is outside the local network, send to gateway:
            gateway_address = self.parent.gateway_local_address()

            # if this is the gateway device:
            if self.address[-1] == gateway_address:
                next_device = self.parent
            else:  # this is not the gateway device:
                dest_local_address = gateway_address
                next_device_address = self.routing_table[dest_local_address][1]
                next_device = self.parent.get_subnetwork_at(next_device_address)

        print("Subnetwork %s sending packet with destination %s to device %s" %
              (self.address, packet.destination, next_device.address))

        # only color edge if not sending packet "upwards"
        if len(self.address) == len(next_device.address):
            self._activate_edge_to(next_device)

        next_device.route(packet)

    def step(self):
        for n in self.network.nodes:
            n['subnetwork'].step()

    '''
        Use this function to get the physical device at the gateway of this subnetwork.
        Recursive. Will always return a NetworkDevice object.
    '''
    def gateway_device(self):
        gateway_subnetwork = self.get_subnetwork_at(self.local_gateway_address)
        return gateway_subnetwork.gateway_device()

    '''
        Convenience method for returning the local address of this network's gateway
    '''
    def gateway_local_address(self):
        return self.network.graph['gateway']

    def get_subnetwork_at(self, at):
        return self.network.nodes[at]['subnetwork']

    def _activate_edge_to(self, other):
        self.model.G.get_edge_data(self.gateway_device().master_address,
                                   other.gateway_device().master_address)["active"] = True

    '''
            Merges the abstract hierarchical graph with the 'master graph' for visualization purposes.
    '''
    def merge_with_master_graph(self):
        for s, d in self.network.edges:
            ns = self.network.nodes[s]['subnetwork'].gateway_device()
            nd = self.network.nodes[d]['subnetwork'].gateway_device()
            ns_address = self.model.address_server[ns.address]
            nd_address = self.model.address_server[nd.address]
            if not self.model.G.get_edge_data(ns_address, nd_address):
                self.model.G.add_edge(ns_address, nd_address)

    def get_device_count(self):
        return self.num_devices



class NetworkDevice(Agent):

    def __init__(self, address, parent, model, routing_table):
        super().__init__(address, model)

        self.parent = parent
        self.routing_table = routing_table
        self.packets_received = 0
        self.packets_sent = 0
        self.address = address

        self.occupying_packets = []

        # retrieve master address
        self.master_address = model.address_server[self.address]

        # append to the main model's device list. For convenience.
        model.devices.append(self)

        # append itself to the master graph
        if self.master_address not in model.G.nodes:
            model.G.add_node(self.master_address)


    def route(self, packet):
        if self.address == packet.destination: # this device is the recipient
            self._receive(packet)
        else:
            self._send(packet)

    '''
        Returns itself. This is the base condition of the SubNetwork.gateway_device() function.
    '''
    def gateway_device(self):
        return self

    '''
        Logic for receiving a network packet.
    '''
    def _receive(self, packet):
        self.packets_received += 1
        self.occupying_packets.append(packet)
        self.model.total_packets_received += 1
        print("Device %s received packet: %s" % (self.address, packet.payload))

    '''
        Logic for sending a network packet.
    '''
    def _send(self, packet):
        if self.address.is_share_subnetwork(packet.destination):  # device is in the local network
            dest_local_address = packet.destination[len(self.address) - 1]
            next_device_address = self.routing_table[dest_local_address][1]
            next_device = self.parent.get_subnetwork_at(next_device_address)
        else:  # device is outside the local network, send to gateway:
            gateway_address = self.parent.gateway_local_address()

            if self.address[-1] == gateway_address: # if this is the gateway device:
                # propagate message "upwards"
                next_device = self.parent
            else:  # this is not the gateway device:
                dest_local_address = gateway_address
                next_device_address = self.routing_table[dest_local_address][1]
                next_device = self.parent.get_subnetwork_at(next_device_address)

        print("Device %s sending packet with destination %s to device %s" %
              (self.address, packet.destination, next_device.address))
        self.packets_sent += 1

        # only color edge if not sending packet "upwards"
        if len(self.address) == len(next_device.address):
            self._activate_edge_to(other=next_device)

        next_device.route(packet)

    def _activate_edge_to(self, other):
        self.model.G.get_edge_data(self.master_address,
                                   other.master_address)["active"] = True

    # def step(self):
    #     r = random.random()
    #     # print(r)
    #     if r < 0.001:
    #         dest = random.choice(self.model.devices).address
    #         packet = Packet(self.model.packet_count, dest, random.choice(self.model.packet_payloads))
    #         self.model.packet_count = self.model.packet_count + 1
    #         print("Device %s attempting to message %s" % (self.address, dest))
    #         self.route(packet)


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

class User(NetworkDevice):
    def __init__(self, active, address, parent, model, routing_table):
        self.active = active
        self.comm_table_in_size = random.randint(2, 10)
        self.comm_table_out_size = random.randint(0, 5)
        self.comm_table_size = self.comm_table_in_size + self.comm_table_out_size
        self.communications_devices = []
        self.communications_freq = []
        self.parent = parent
        self.address = address
        super().__init__(address, parent, model, routing_table)



    def step(self):
        if(len(self.communications_devices) == 0):
            for i in range(self.comm_table_in_size):
                dest = random.choice(self.parent.children).address
                freq = random.random()
                self.communications_devices.append(dest)
                self.communications_freq.append(freq)

            for i in range(self.comm_table_out_size):
                dest = random.choice(self.model.devices).address
                if (not self.address.is_share_subnetwork(dest)):
                    freq = random.random()
                    self.communications_devices.append(dest)
                    self.communications_freq.append(freq)
                else: i -= 1

        r = random.random()
        if r < self.active: #TODO establish connection
            dest = self.communications_devices[random.randint(0,len(self.communications_devices) - 1)]
            packet = Packet(self.model.packet_count, dest, random.choice(self.model.packet_payloads))
            self.model.packet_count = self.model.packet_count + 1
            print("User %s attempting to message %s" % (self.address, dest))
            self.route(packet)

