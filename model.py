from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector
from agents.subnetworks import *
import math

import numpy as np

VERBOSE = True


def get_total_compromised(model):
    return model.total_compromised

def get_share(model):
    avg = 0
    for i in range(model.num_subnetworks - 1):
        for j in range(i + 1, model.num_subnetworks - 1):
            avg += model.closeness_matrix[i][j]
    n = model.num_subnetworks - 1
    return avg / (n * (n-1) / 2)  # avg / n choose 2

class CybCim(Model):

    def __init__(self,
                 num_internet_devices=100,
                 num_subnetworks=15,
                 num_attackers=5,
                 device_count=30,
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
                 transitivity=1):
        global VERBOSE
        super().__init__()

        self.G = nx.Graph()  # master graph
        self.G.graph['interactive'] = interactive  # adjustable parameter, affects network visualization
        self.G.graph['fisheye'] = fisheye  # adjustable parameter, affects network visualization
        self.G.graph['visualize'] = visualize  # adjustable parameter, affects network visualization

        self.address_server = AddressServer()

        self.num_internet_devices = num_internet_devices  # adjustable parameter, possibly useless?
        self.num_subnetworks = num_subnetworks  # adjustable parameter
        self.num_attackers = num_attackers  # adjustable parameter

        self.information_importance = information_importance  # adjustable parameter
        self.device_security_deviation_width = device_security_deviation_width  # adjustable parameter
        self.information_gain_weight = information_gain_weight  # adjustable parameter
        self.passive_detection_weight = passive_detection_weight  # adjustable parameter
        self.spread_detection_weight = spread_detection_weight  # adjustable parameter
        self.target_detection_weight = target_detection_weight  # adjustable parameter

        self.num_users = 0
        self.avg_time_to_new_attack = avg_time_to_new_attack  # adjustable parameter
        self.device_count = device_count  # adjustable parameter
        self.reciprocity = reciprocity  # adjustable parameter
        self.transitivity = transitivity  # adjustable parameter TODO: turn off permanently?
        self.verbose = verbose  # adjustable parameter
        VERBOSE = verbose

        self.devices = []
        self.subnetworks = []
        self.organizations = []
        self.users = []  # keeping track of human users in all networks
        self.attackers = []

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
        self.total_packets_received = 0  # unneccessary
        self.total_failure_count = 0  # unneccessary
        self.total_compromised = 0
        self.packet_count = 1  # maybe have it do something with org productivity?

        # TODO make parameter?
        self.initial_closeness = 0.1  # initial closeness between organizations

        # TODO possibly move to own function
        # initialize a n*n matrix to store sharing decision disregarding attacker subnetwork
        self.closeness_matrix = np.full((self.num_subnetworks - 1, self.num_subnetworks - 1), self.initial_closeness)

        self.datacollector = DataCollector(
            {
             "Compromised Devices": get_total_compromised,
            "Closeness": get_share
            }
        )

        self.running = True
        self.datacollector.collect(self)
        if VERBOSE:  # TODO: change to use a dedicated logging class/logger
            print("Starting!")
            print("Number of devices: %d" % len(self.devices))

    def _create_graph(self):
        self.network = random_mesh_graph(self.num_subnetworks)

    def _create_devices(self, subgraph_type):
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]

            n = get_subnetwork_device_count(self)  # randomly generates device count
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
        # TODO: implement trust factor
        for i in range(self.num_subnetworks - 1):
            for j in range(i + 1, self.num_subnetworks - 1): # only visit top matrix triangle
                r = random.random()
                if self.closeness_matrix[i][j] > r:  # will interact event
                    closeness = self.closeness_matrix[i][j]
                    r1, r2 = self.subnetworks[i].share_information(closeness), self.subnetworks[j].share_information(closeness)
                    choice = [r1, r2]
                    if sum(choice) == 2:  # both cooperate/share
                        self.closeness_matrix[i][j] = get_reciprocity(sum(choice), closeness, self.reciprocity)
                        self.closeness_matrix[j][i] = get_reciprocity(sum(choice), closeness, self.reciprocity)
                        self.adjust_transitivity(i, j)

                        self.share_info_cooperative(self.subnetworks[i], self.subnetworks[j])
                        self.share_info_cooperative(self.subnetworks[j], self.subnetworks[i])

                        self.subnetworks[i].update_information_utility()
                        self.subnetworks[j].update_information_utility()

                    elif sum(choice) == 0:  # both defect
                        self.closeness_matrix[i][j] = get_reciprocity(sum(choice), closeness, self.reciprocity)
                        self.closeness_matrix[j][i] = get_reciprocity(sum(choice), closeness, self.reciprocity)
                    elif sum(choice) == 1: # one defects and one cooperates #no change in closeness #TODO implement different behaviour?
                        if choice[0] == 1:
                            self.share_info_selfish(self.subnetworks[i], self.subnetworks[j])
                            self.subnetworks[i].update_information_utility()
                        else:
                            self.share_info_selfish(self.subnetworks[j], self.subnetworks[i])
                            self.subnetworks[j].update_information_utility()

    def share_info_selfish(self, org1, org2):
        for attack, info in org1.attacks_list.items():
            org2.attacks_list[attack] = get_new_information_selfish(org2.attacks_list[attack], info)

    def share_info_cooperative(self, org1, org2):
        for attack, info in org1.attacks_list.items():
            org2.attacks_list[attack] = get_new_information_cooperative(org2.attacks_list[attack], info)

    def get_closeness(self, i, j):
        if i > j:
            j, i = i, j
        return self.closeness_matrix[i, j]

    def adjust_transitivity(self, org1, org2):
        for i in range(self.num_subnetworks - 1):
            if i == org1 or i == org2:
                continue
            else:
                if abs(0.5 - self.closeness_matrix[org1][i]) > abs(0.5 - self.closeness_matrix[org2][i]):
                    # if org1's opinion is more "extreme" than org2
                    self.closeness_matrix[org2][i] /= self.transitivity
                else:
                    # otherwise
                    self.closeness_matrix[org1][i] /= self.transitivity


    def step(self):
        self.update_closeness()  # TODO: move after agent step???
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
