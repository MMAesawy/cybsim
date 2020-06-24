from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector
from agents.subnetworks import *

import numpy as np

VERBOSE = True


def get_total_compromised(model):
    return model.total_compromised

def get_share(model):
    # np.mean(model.closeness_matrix)
    avg = 0
    for i in range(model.num_subnetworks - 1):
        for j in range(i + 1, model.num_subnetworks - 1):
            avg += model.closeness_matrix[i][j]
    return avg / ((model.num_subnetworks - 1)**2 - (model.num_subnetworks - 1)) / 2 

class CybCim(Model):

    def __init__(self,
                 num_internet_devices=100,
                 num_subnetworks=15,
                 num_attackers=5,
                 # max_hops=3,
                 # min_capacity=10,
                 # max_capacity=20,
                 min_device_count=5,
                 max_device_count=50,
                 avg_time_to_new_attack=50,
                 information_importance=2,
                 device_security_deviation_width=0.25,
                 information_gain_weight=0.5,
                 passive_detection_weight=0.125,
                 spread_detection_weight=0.25,
                 target_detection_weight=1.0,
                 interactive=True,
                 fisheye=True,
                 subgraph_type=True,
                 visualize=True,
                 verbose=True,
                 reciprocity=2,
                 transitivity=2):
        global VERBOSE
        super().__init__()

        self.G = nx.Graph()  # master graph
        self.G.graph['interactive'] = interactive
        self.G.graph['fisheye'] = fisheye
        self.G.graph['visualize'] = visualize

        self.address_server = AddressServer()

        self.num_internet_devices = num_internet_devices
        self.num_subnetworks = num_subnetworks
        self.num_attackers = num_attackers
        # self.subnetworks = []

        self.information_importance = information_importance
        self.device_security_deviation_width = device_security_deviation_width
        self.information_gain_weight = information_gain_weight
        self.passive_detection_weight = passive_detection_weight
        self.spread_detection_weight = spread_detection_weight
        self.target_detection_weight = target_detection_weight

        # self.max_hops = max_hops
        # self.min_capacity = min_capacity
        # self.max_capacity = max_capacity
        self.num_users = 0
        self.avg_time_to_new_attack = avg_time_to_new_attack
        self.min_device_count = min_device_count
        self.max_device_count = max_device_count
        self.verbose = verbose
        VERBOSE = verbose

        # avg_node_degree = 3
        self.devices = []
        self.subnetworks = []
        self.users = []  # keeping track of human users in all networks
        # self.active_correspondences = []

        # create graph and compute pairwise shortest paths
        self._create_graph()

        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.network))

        # construct subnetworks that compose the main network
        self._create_devices(subgraph_type)

        # add nodes to master graph
        self.merge_with_master_graph()

        self.reset_edge_data()

        # initialize agents
        self.grid = NetworkGrid(self.G)
        self.schedule = SimultaneousActivation(self)
        for d in self.devices:
            self.grid.place_agent(d, self.address_server[d.address])
            self.schedule.add(d)
        for o in self.subnetworks:
            self.schedule.add(o)
        self.total_packets_received = 0
        self.total_failure_count = 0
        self.total_compromised = 0
        self.packet_count = 1
        self.initial_closeness = 0.5 # initial closeness between organizations
        # can be parameterized
        self.reciprocity = reciprocity
        self.transitivity = transitivity

        #initialize a n*n matrix to store sharing decision disregarding attacker subnetwork
        self.closeness_matrix = np.full((self.num_subnetworks - 1, self.num_subnetworks - 1), 0.5)

        self.datacollector = DataCollector(
            {
             "Compromised Devices": get_total_compromised,
            "Closeness": get_share #testing
            }
        )

        self.running = True
        self.datacollector.collect(self)
        if VERBOSE:
            print("Starting!")
            print("Number of devices: %d" % len(self.devices))

    def _create_graph(self):
        self.network = random_mesh_graph(self.num_subnetworks)

    def _create_devices(self, subgraph_type):
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]

            n = get_subnetwork_device_count(self)
            of = 'devices' if subgraph_type else 'subnetworks'

            if len(self.network.nodes) == i + 1:  # the last node of the network is always an attackers subnetwork
                self.network.nodes[i]['subnetwork'] = Attackers(address=Address(i),
                                                                parent=self,
                                                                model=self,
                                                                routing_table=routing_table,
                                                                initial_attack_count=self.num_attackers,
                                                                of='devices',
                                                                avg_time_to_attack_gen=self.avg_time_to_new_attack)
            else:
                self.network.nodes[i]['subnetwork'] = Organization(address=Address(i),
                                                                   parent=self,
                                                                   model=self,
                                                                   routing_table=routing_table,
                                                                   num_devices=n,
                                                                   of=of)

    def get_subnetwork_at(self, at):
        return self.network.nodes[at]['subnetwork']

    def reset_edge_data(self):
        # deactivate all edges
        for edge in self.G.edges(data=True):
            edge[2]["active"] = False
            edge[2]["malicious"] = False

    def update_closeness(self):
        # n = random.randint(0, self.num_subnetworks - 1)
        # m = random.randint(0, self.num_subnetworks - 1)
        # while (n != m):
        #     m = random.randint(0, self.num_subnetworks - 1)

        for i in range(self.num_subnetworks - 1):
            for j in range(i + 1, self.num_subnetworks - 1): # only visit top matrix triangle
                # if i == j: # or type(self.subnetworks[i]) is Attackers or type(self.subnetworks[j]) is Attackers:
                #     continue
                # else:
                r = random.random()
                if (self.closeness_matrix[i][j] > r): #will interact
                    closeness = self.closeness_matrix[i][j]
                    r1, r2 = self.subnetworks[i].share_information(closeness), self.subnetworks[j].share_information(closeness)
                    choice = [int(r1 > closeness), int(r2 > closeness)]
                    if sum(choice) == 2:  # both cooperate
                        self.closeness_matrix[i][j] = 1 - ((1 - closeness) / self.reciprocity)
                        self.closeness_matrix[j][i] = 1 - ((1 - closeness) / self.reciprocity)
                        self.adjust_closeness(i, j)
                    elif sum(choice) == 0:  # both defect
                        self.closeness_matrix[i][j] = closeness / self.reciprocity
                        self.closeness_matrix[j][i] = closeness / self.reciprocity
                    else:  # one defects and one cooperates #no change in closeness #TODO implement different behaviour?
                        pass

    def adjust_closeness(self, org1, org2):
        for i in range(self.num_subnetworks - 1):
            if i == org1 or i == org2:
                continue
            else:
                if abs(0.5 - self.closeness_matrix[org1][i]) > abs(0.5 - self.closeness_matrix[org2][i]):
                    self.closeness_matrix[org2][i] /= self.transitivity
                else:
                    self.closeness_matrix[org1][i] /= self.transitivity


    def step(self):
        self.update_closeness()
        self.reset_edge_data()

        # update agents
        self.schedule.step()

        # # update correspondences
        # i = 0
        # while True:
        #     c = self.active_correspondences[i]
        #     if not c.active:
        #         self.active_correspondences.pop(i)
        #     else:
        #         c.step()
        #         i += 1
        #     if i >= len(self.active_correspondences):
        #         break
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
                e_data = self.G.get_edge_data(ns_address, nd_address)
                e_data["active"] = False
                e_data["malicious"] = False
