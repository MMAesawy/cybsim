from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector
from helpers import *
from agents.devices import *
from agents.constructs import *
from agents.agents import *
from agents.subnetworks import *

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
                 # max_hops=3,
                 # min_capacity=10,
                 # max_capacity=20,
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
        # self.max_hops = max_hops
        # self.min_capacity = min_capacity
        # self.max_capacity = max_capacity
        self.num_users = 0
        self.min_device_count = min_device_count
        self.max_device_count = max_device_count
        self.verbose = verbose
        VERBOSE = verbose

        #avg_node_degree = 3
        self.devices = []
        self.active_correspondences = []

        # create graph and compute pairwise shortest paths
        self._create_graph()

        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.network))

        # construct subnetworks that compose the main network
        self._create_devices(subgraph_type)


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

    def _create_graph(self):
        self.network = random_mesh_graph(self.num_internet_devices)

    def _create_devices(self, subgraph_type):
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]

            n = get_subnetwork_device_count(self)
            of = 'devices' if subgraph_type else 'subnetworks'

            self.network.nodes[i]['subnetwork'] = Organization(address=Address(i),
                                                               parent=self,
                                                               model=self,
                                                               routing_table=routing_table,
                                                               num_devices=n,
                                                               of=of
                                                 )

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




