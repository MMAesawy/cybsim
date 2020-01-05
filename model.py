from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector
from helpers import *
from agents.devices import *
from agents.constructs import *
from agents.agents import *

import numpy as np

VERBOSE = True

def get_total_packets_received(model):
    return model.total_packets_received

def get_total_packets_failed(model):
    return model.total_failure_count

class CybCim(Model):

    def __init__(self,
                 num_internet_devices= 100,
                 num_subnetworks= 15,
                 max_hops=3,
                 min_capacity=10,
                 max_capacity=20,
                 min_device_count = 5,
                 max_device_count = 50,
                 interactive=True,
                 fisheye=True,
                 subgraph_type=True,
                 visualize=True,
                 verbose=True):
        global VERBOSE
        super().__init__()

        self.G = nx.Graph() # master graph
        self.G.graph['interactive'] = interactive
        self.G.graph['fisheye'] = fisheye
        self.G.graph['visualize'] = visualize

        self.address_server = AddressServer()

        self.num_internet_devices = num_internet_devices
        self.num_subnetworks = num_subnetworks
        self.max_hops = max_hops
        self.min_capacity = min_capacity
        self.max_capacity = max_capacity
        self.num_users = 0
        self.min_device_count = min_device_count
        self.max_device_count = max_device_count
        self.verbose = verbose
        VERBOSE = verbose

        #avg_node_degree = 3
        self.devices = []
        self.active_correspondences = []

        # create graph and compute pairwise shortest paths
        self.network = get_random_graph(self.num_subnetworks, avg_node_degree=2)
        # self.network = nx.barabasi_albert_graph(self.num_subnetworks, min(2, self.num_subnetworks - 1))
        # self.network.graph['gateway'] = np.argmax([self.network.degree(i) for i in self.network.nodes])

        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.network))

        # construct subnetworks that compose the main network
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]
            if i == self.network.graph['gateway']:
                n = self.num_internet_devices
                of = 'devices'
            else:
                n = get_subnetwork_device_count(self)
                of = 'devices' if subgraph_type else 'subnetworks'

            self.network.nodes[i]['subnetwork']  =  SubNetwork(address=Address(i),
                                                               parent=self,
                                                               model=self,
                                                               routing_table=routing_table,
                                                               avg_node_degree=1,
                                                               num_devices=n,
                                                               of=of
                                                 )


        # add nodes to master graph
        self.merge_with_master_graph()

        # initialize edge 'active' attribute
        for edge in self.G.edges(data=True):
            edge[2]["active"] = False

        # initialize agents
        self.grid = NetworkGrid(self.G)
        self.schedule = SimultaneousActivation(self)
        for d in self.devices:
            self.grid.place_agent(d, self.address_server[d.address])
            self.schedule.add(d)
        self.total_packets_received = 0
        self.total_failure_count = 0
        self.packet_count = 1

        self.datacollector = DataCollector(
            {"Packets Received": get_total_packets_received,
            "Packets Dropped": get_total_packets_failed,}
        )

        self.running = True
        self.datacollector.collect(self)
        if VERBOSE:
            print("Starting!")
            print("Number of devices: %d" % len(self.devices))

    def get_subnetwork_at(self, at):
        return self.network.nodes[at]['subnetwork']

    def step(self):
        # deactivate all edges
        for edge in self.G.edges(data=True):
            edge[2]["active"] = False
        # update agents
        self.schedule.step()

        # update correspondences
        i = 0
        while True:
            c = self.active_correspondences[i]
            if not c.active:
                self.active_correspondences.pop(i)
            else:
                c.step()
                i += 1
            if i >= len(self.active_correspondences):
                break
        self.datacollector.collect(self)

    def merge_with_master_graph(self):
        """Merges the abstract hierarchical graph with the 'master graph' for visualization purposes."""
        # add nodes to master graph
        for s, d in self.network.edges:
            ns = self.get_subnetwork_at(s).gateway_device()
            nd = self.get_subnetwork_at(d).gateway_device()
            ns_address = self.address_server[ns.address]  # creates address entry if it does not exist
            nd_address = self.address_server[nd.address]  # creates address entry if it does not exist
            if not self.G.get_edge_data(ns_address, nd_address):
                self.G.add_edge(ns_address, nd_address)


class SubNetwork:
    def __init__(self, address, parent, model, routing_table, num_devices, of='subnetworks', avg_node_degree=2):
        self.address = address
        self.parent = parent
        self.model = model
        self.routing_table = routing_table
        self.of = of
        self.num_devices = num_devices
        self.current_packets = []

        # does not play into anything currently
        if of == 'devices':
            self.type = self.get_subnetwork_type()
            self.success_percentage = 0

        # create graph and compute pairwise shortest paths
        self.network = get_random_graph(self.num_devices, avg_node_degree)
        # self.network = nx.barabasi_albert_graph(self.num_devices, min(1, self.num_devices-1))
        # self.network.graph['gateway'] = np.argmax([self.network.degree(i) for i in self.network.nodes])
        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.network))

        self.local_gateway_address = self.network.graph['gateway']

        self.children = []
        self.num_users = 0
        # create objects to be stored within the graph
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]
            if of == 'subnetworks': # if this is a subnetwork of subnetworks:
                n = SubNetwork(address=self.address + i,
                                 parent=self,
                                 model=model,
                                 routing_table=routing_table,
                                 num_devices=get_subnetwork_device_count(self.model),
                                 of='devices')
                self.num_users += n.num_users
                self.network.nodes[i]['subnetwork'] = n
            elif of == 'devices': # if this is a subnetwork of devices
                self.num_users = get_subnetwork_user_count(self.num_devices)
                if (i <= self.num_users):
                    activity = random.random() / 10
                    self.network.nodes[i]['subnetwork'] = User(activity=activity,
                                                                address=self.address + i,
                                                                parent=self,
                                                                model=model,
                                                                routing_table=routing_table)
                else:
                    self.network.nodes[i]['subnetwork'] = NetworkDevice(address=self.address + i,
                                                                    parent=self,
                                                                    model=model,
                                                                    routing_table=routing_table)
                self.children.append(self.network.nodes[i]['subnetwork'])

        self.model.num_users += self.num_users

        # add nodes to master graph
        self.merge_with_master_graph()

    def get_next_gateway(self, packet):
        """
        Logic for sending a network packet.
        :param packet: the packet to send
        """
        if self.address.is_share_subnetwork(packet.destination): # device is in the local network
            dest_local_address = packet.destination[len(self.address) - 1]
            next_device_address = self.routing_table[dest_local_address][1]
            next_device = self.parent.get_subnetwork_at(next_device_address).gateway_device()
        else:  # device is outside the local network, send to gateway:
            gateway_address = self.parent.gateway_local_address()
             # if this is the gateway device: (propagate upwards)
            if self.address[-1] == gateway_address:
                next_device = self.parent.get_next_gateway(packet)
            else:  # this is not the gateway device:
                dest_local_address = gateway_address
                next_device_address = self.routing_table[dest_local_address][1]
                next_device = self.parent.get_subnetwork_at(next_device_address).gateway_device()

        return next_device

    def gateway_device(self):
        """
        Use this function to get the physical device at the gateway of this subnetwork.
        Recursive. Will always return a NetworkDevice object.
        :return: returns the physical NetworkDevice object which acts as a gateway
        """
        gateway_subnetwork = self.get_subnetwork_at(self.local_gateway_address)
        return gateway_subnetwork.gateway_device()

    def gateway_local_address(self):
        """
        Convenience method for returning the local address of this network's gateway
        :return: this subnetwork's gateway node address/number
        """
        return self.network.graph['gateway']

    def get_subnetwork_at(self, at):
        return self.network.nodes[at]['subnetwork']

    def _activate_edge_to(self, other):
        self.model.G.get_edge_data(self.gateway_device().master_address,
                                   other.gateway_device().master_address)["active"] = True

    def merge_with_master_graph(self):
        """Merges the abstract hierarchical graph with the 'master graph' for visualization purposes."""
        for s, d in self.network.edges:
            ns = self.network.nodes[s]['subnetwork'].gateway_device()
            nd = self.network.nodes[d]['subnetwork'].gateway_device()
            ns_address = self.model.address_server[ns.address]
            nd_address = self.model.address_server[nd.address]
            if not self.model.G.get_edge_data(ns_address, nd_address):
                self.model.G.add_edge(ns_address, nd_address)

    def get_device_count(self):
        return self.num_devices

    # can be changed later
    def get_subnetwork_type(self):
        if 5 <= self.num_devices <= 15:
            return 'private_network'
        elif 16 <= self.num_devices <= 25:
            return 'startup'
        elif 26 <= self.num_devices <= 35:
            return 'small_company'
        elif 36 <= self.num_devices <= 50:
            return 'large_company'
        else:
            return 'internet_device'



