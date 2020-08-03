from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector
from agents.subnetworks import *
import math

import numpy as np

VERBOSE = True

# Data collector function for total compromised
def get_total_compromised(model):
    return model.total_compromised

# Data collector function for closeness between organization
def get_avg_closeness(model):
    avg = 0
    for i in range(model.num_subnetworks - 1):
        for j in range(i + 1, model.num_subnetworks - 1):
            avg += model.closeness_matrix[i, j]
    n = model.num_subnetworks - 1
    return avg / (n * (n-1) / 2)  # avg / n choose 2

def get_avg_utility(model):
    avg = model.org_utility / (model.num_subnetworks - 1)
    model.org_utility = 0
    return avg

class CybCim(Model):

    def __init__(self,
                 interactive=True,
                 fisheye=True,
                 subgraph_type=True,
                 visualize=True,
                 verbose=True,
                 information_sharing=True,
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
                 reciprocity=2,
                 transitivity=1,
                 trust_factor=2,
                 initial_closeness=0.5,
                 initial_trust=0.5):

        global VERBOSE
        super().__init__()

        self.G = nx.Graph()  # master graph
        self.G.graph['interactive'] = interactive  # adjustable parameter, affects network visualization
        self.G.graph['fisheye'] = fisheye  # adjustable parameter, affects network visualization
        self.G.graph['visualize'] = visualize  # adjustable parameter, affects network visualization
        self.verbose = verbose  # adjustable parameter
        VERBOSE = verbose
        self.address_server = AddressServer()

        # For batch runner
        self.running = True

        self.num_internet_devices = num_internet_devices  # adjustable parameter, possibly useless?
        self.num_subnetworks = num_subnetworks  # adjustable parameter
        self.num_attackers = num_attackers  # adjustable parameter
        self.device_count = device_count  # adjustable parameter
        self.avg_time_to_new_attack = avg_time_to_new_attack  # adjustable parameter
        self.information_importance = information_importance  # adjustable parameter
        self.device_security_deviation_width = device_security_deviation_width  # adjustable parameter
        self.information_gain_weight = information_gain_weight  # adjustable parameter
        self.passive_detection_weight = passive_detection_weight  # adjustable parameter
        self.spread_detection_weight = spread_detection_weight  # adjustable parameter
        self.target_detection_weight = target_detection_weight  # adjustable parameter
        self.reciprocity = reciprocity  # adjustable parameter
        self.transitivity = transitivity  # adjustable parameter TODO: turn off permanently?
        self.trust_factor = trust_factor  # adjustable parameter
        self.initial_closeness = initial_closeness  # adjustable parameter
        self.initial_trust = initial_trust  # adjustable parameter
        self.information_sharing = information_sharing  # adjustable parameter

        self.num_users = 0
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
        self.packet_count = 1  # TODO maybe have it do something with org productivity?

        self.org_utility = 0

        # TODO possibly move to own function
        # initialize a n*n matrix to store organization closeness disregarding attacker subnetwork
        self.closeness_matrix = np.full((self.num_subnetworks - 1, self.num_subnetworks - 1), self.initial_closeness, dtype=np.float)

        # initialize a n*n matrix to store organization's trust towards each other disregarding attacker subnetwork
        self.trust_matrix = np.full((self.num_subnetworks - 1, self.num_subnetworks - 1), self.initial_trust, dtype=np.float)

        # makes the trust factor between an organization and itself zero in order to avoid any average calculation errors
        np.fill_diagonal(self.trust_matrix, 0)

        # data needed for making any graphs
        self.datacollector = DataCollector(
            {
             "Compromised Devices": get_total_compromised,
             "Closeness": get_avg_closeness,
             "Utility": get_avg_utility
            }
        )

        self.running = True
        self.datacollector.collect(self)
        if VERBOSE:  # TODO: change to use a dedicated logging class/logger
            print("Starting!")
            print("Number of devices: %d" % len(self.devices))


    # <------ creating the graph and defining respective organization/attacker subnetworks ------>
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

    def information_sharing_game(self):
        # TODO: implement trust factor
        for i in range(self.num_subnetworks - 1):
            for j in range(i + 1, self.num_subnetworks - 1): # only visit top matrix triangle
                r = random.random()
                if self.closeness_matrix[i, j] > r:  # will interact event
                    t1 = self.trust_matrix[i, j]
                    t2 = self.trust_matrix[j, i]
                    closeness = self.closeness_matrix[i][j]
                    # get each organization's decision to share or not based on its trust towards the other
                    r1, r2 = self.subnetworks[i].share_decision(t1), self.subnetworks[j].share_decision(t2)
                    choice = [r1, r2]
                    if sum(choice) == 2:  # both cooperate/share
                        # come closer to each other for both orgs (symmetric matrix)
                        self.closeness_matrix[i, j] = get_reciprocity(sum(choice), closeness, self.reciprocity)
                        self.closeness_matrix[j, i] = get_reciprocity(sum(choice), closeness, self.reciprocity)

                        # trust will increase for both organizations
                        self.trust_matrix[i, j] = increase_trust(t1, self.trust_factor)
                        self.trust_matrix[j, i] = increase_trust(t2, self.trust_factor)

                        adjust_transitivity(self, i, j)

                        # actually gain information for both organizations
                        share_info_cooperative(self.subnetworks[i], self.subnetworks[j])
                        share_info_cooperative(self.subnetworks[j], self.subnetworks[i])

                        # lose some utility when sharing due to privacy loss etc
                        self.subnetworks[i].update_information_utility()
                        self.subnetworks[j].update_information_utility()

                    elif sum(choice) == 0:  # both defect
                        # grow further away from each other for both orgs (symmetric matrix)
                        self.closeness_matrix[i, j] = get_reciprocity(sum(choice), closeness, self.reciprocity)
                        self.closeness_matrix[j, i] = get_reciprocity(sum(choice), closeness, self.reciprocity)

                        # trust will not be affected in this case

                    # one defects and one cooperates #no change in closeness #TODO implement different behaviour?
                    elif sum(choice) == 1:
                        if choice[0] == 1: # only org i shares
                            share_info_selfish(self.subnetworks[i], self.subnetworks[j])
                            self.subnetworks[i].update_information_utility()
                            self.trust_matrix[i, j] = decrease_trust(t1, self.trust_factor) # org i will trust org j less
                            # org j will nto update its trust

                        else: # org j shares
                            share_info_selfish(self.subnetworks[j], self.subnetworks[i])
                            self.subnetworks[j].update_information_utility()
                            self.trust_matrix[j, i] = decrease_trust(t2, self.trust_factor) # org j will trust org i less
                            #org i will not update its trust

    def get_closeness(self, i, j):
        if i > j:
            j, i = i, j
        return self.closeness_matrix[i, j]

    def step(self):
        if self.information_sharing:
            self.information_sharing_game()  # TODO: move after agent step???
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
