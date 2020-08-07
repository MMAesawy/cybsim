import math
from helpers import *
from agents.agents import *
from abc import ABC, abstractmethod
from mesa.agent import Agent
from collections import defaultdict
import random
import numpy as np


class SubNetwork(ABC):

    @abstractmethod
    def _create_graph(self):
        avg_node_degree = 1
        # create graph and compute pairwise shortest paths
        self.network = random_star_graph(self.num_devices, avg_node_degree)
        # self.network = nx.barabasi_albert_graph(self.num_devices, min(1, self.num_devices-1))
        # self.network.graph['gateway'] = np.argmax([self.network.degree(i) for i in self.network.nodes])

    @abstractmethod
    def _create_devices(self):
        of = self.of  # 'devices'
        self.children = []
        self.num_users = 0
        # create objects to be stored within the graph
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]
            if of == 'subnetworks':  # if this is a subnetwork of subnetworks:
                n = SubNetwork(address=self.address + i,
                               parent=self,
                               model=self.model,
                               routing_table=routing_table,
                               num_devices=get_subnetwork_device_count(self.model),
                               of='devices')
                self.num_users += n.num_users
                self.network.nodes[i]['subnetwork'] = n
            elif of == 'devices':  # if this is a subnetwork of devices
                self.num_users = get_subnetwork_user_count(self.num_devices)
                if (i <= self.num_users):
                    activity = random.random() / 10
                    self.network.nodes[i]['subnetwork'] = User(activity=activity,
                                                               address=self.address + i,
                                                               parent=self,
                                                               model=self.model,
                                                               routing_table=routing_table)
                else:
                    self.network.nodes[i]['subnetwork'] = NetworkDevice(address=self.address + i,
                                                                        parent=self,
                                                                        model=self.model,
                                                                        routing_table=routing_table)
                self.children.append(self.network.nodes[i]['subnetwork'])

    def __init__(self, address, parent, model, routing_table, num_devices, of='subnetworks'):
        self.address = address
        self.parent = parent
        self.model = model
        self.routing_table = routing_table
        self.of = of
        self.num_devices = num_devices
        self.current_packets = []
        self.users = []

        self._create_graph()

        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.network))
        self.local_gateway_address = self.network.graph['gateway']
        model.subnetworks.append(self)

        self._create_devices()

        # add nodes to master graph
        self.merge_with_master_graph()

    def get_next_gateway(self, packet):
        """
        Logic for sending a network packet.
        :param packet: the packet to send
        """
        if self.address.is_share_subnetwork(packet.destination.address):  # device is in the local network
            dest_local_address = packet.destination.address[len(self.address) - 1]
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
                e_data = self.model.G.get_edge_data(ns_address, nd_address)
                e_data["active"] = False
                e_data["malicious"] = False

    def get_device_count(self):
        return self.num_devices


class Organization(SubNetwork, Agent):
    organization_count = 0

    def __init__(self, address, parent, model, routing_table, num_devices, of='subnetworks'):
        SubNetwork.__init__(self, address, parent, model, routing_table, num_devices, of)
        Agent.__init__(self, address, model)
        self.old_utility = 0
        self.utility = 0
        self.old_attacks_list = defaultdict(lambda: np.zeros(1000, dtype=np.bool))
        self.new_attacks_list = defaultdict(lambda: np.zeros(1000, dtype=np.bool))
        self.attacks_compromised_counts = defaultdict(lambda: 0)
        # self.org_out = np.zeros(len(model.organizations))
        self.org_out = defaultdict(lambda: 0)

        # incident start, last update
        self.attack_awareness = defaultdict(lambda: [self.model.schedule.time, self.model.schedule.time])
        self.security_budget = max(0.005, min(1, random.gauss(0.5, 1 / 6)))
        # self.security_budget = 0.005
        self.num_compromised_new = 0  # for getting avg rate of compromised per step
        self.num_compromised_old = 0  # for getting avg rate of compromised per step
        self.count = 0
        self.risk_of_sharing = 0.3  # TODO: parametrize, possibly update in update_utility_sharing or whatever
        self.info_in = 0
        self.info_out = 0
        self.num_detect = defaultdict(lambda: 0)
        self.num_attempts = 0
        self.security_drop = min(1, max(0, random.gauss(0.75, 0.05)))
        self.acceptable_freeload = model.acceptable_freeload


        # <---- Data collection ---->

        self.free_loading_ratio = 0  # variable to store freeloading ratio for each organization
        # to store changing organization security
        self.total_security = 0  # used for batch runner
        self.avg_security = 0

        self.compromised_per_step_aggregated = 0
        self.avg_compromised_per_step = 0  # TODO yet to be used

        self.incident_times = 0  # for avg incident time
        self.avg_incident_times = 0  # for avg incident time
        self.incident_times_num = 0  # for avg incident time

        # to store times organization shares when it enters a game
        self.total_share = 0
        self.avg_share = 0
        self.num_games_played = 0

        # to store average known info
        self.avg_info = 0

        # <--- adding organization to model org array and setting unique ID --->

        model.organizations.append(self)
        # set and increment id
        self.id = Organization.organization_count
        Organization.organization_count += 1

    def get_avg_known_info(self):
        avg = 0
        for attack, info in self.old_attacks_list.items():
            avg += info.mean()
        return avg / len(self.old_attacks_list)

    def get_avg_security(self):
        return self.total_security / (self.model.schedule.time + 1)

    def get_free_loading_ratio(self):
        return self.info_in / (self.info_in + self.info_out + 1e-5)

    def share_decision(self, org2, trust):
        """Returns whether or not to share information according to other party."""
        self.num_games_played += 1
        info_out = self.org_out[org2]  # org1 out (org1_info_out)
        info_in = org2.org_out[self]  # org1 in (org2_info_out)
        if info_out > info_in:  # decreases probability to share
            share = random.random() < trust * min(1, self.acceptable_freeload + (info_in / info_out))
        else:
            share = random.random() < trust
        if share:
            self.total_share += 1
        return share

    def get_avg_share(self):
        return self.total_share / self.num_games_played

    def update_budget(self):
        unhandled_attacks = []
        current_time = self.model.schedule.time
        for a, v in self.attack_awareness.items():
            incident_time = current_time - v[0]
            if incident_time > self.model.org_memory:
                unhandled_attacks.append((self.num_detect[a], incident_time))

        if unhandled_attacks:  # a security incident happened and wasn't handled in time
            ratio = sum(
                [num_detected / self.num_users / inc_time for num_detected, inc_time in unhandled_attacks]) / len(
                unhandled_attacks)
            self.security_budget += (1 - self.security_budget) * ratio
        else:
            print("Dropping security by", self.security_drop)
            self.security_budget *= self.security_drop  # TODO: change for each org?

        self.security_budget = max(0.005, min(1.0, self.security_budget))

        # self.security_budget = max(0, min(1, random.gauss(0.5, 1 / 6)))

    def update_budget_utility(self):
        # self.utility -= self.security_budget ** 2
        pass

    def update_stay_utility(self, num_compromised):
        self.utility -= (num_compromised / self.num_users) ** 2

    def update_information_utility(self):
        # self.utility -= self.risk_of_sharing
        pass

    def update_incident_times(self, attack):
        current_time = self.model.schedule.time
        self.model.incident_times.append(current_time - self.attack_awareness[attack][0])
        self.incident_times += (current_time - self.attack_awareness[attack][0])  # for avg incident time

    def set_avg_incident_time(self):  # for avg incident time
        return self.incident_times / self.incident_times_num

    def clear_awareness(self, attack):
        self.update_incident_times(attack)
        self.incident_times_num += 1  # for avg incident time
        self.avg_incident_times = self.set_avg_incident_time()
        del self.attack_awareness[attack]
        del self.num_detect[attack]

    def is_aware(self, attack):
        return attack in self.attack_awareness

    def get_percent_compromised(self, attack=None):
        """Returns the percentage of users compromised for each attack (or the total if `attack` is None)"""
        if not self.num_users:
            return 0
        if attack:
            return self.attacks_compromised_counts[attack] / self.num_users
        return self.num_compromised_old / self.num_users

    def get_info(self, attack):
        return self.old_attacks_list[attack].mean()

    def set_avg_compromised_per_step(self):
        return self.compromised_per_step_aggregated / (self.model.schedule.time + 1)

    def step(self):
        for c in self.attacks_compromised_counts.values():
            self.update_stay_utility(c)

        self.count += 1
        # organization updates its security budget every n steps based on previous step utility in order to improve its utility
        if self.count == self.model.security_update_interval:
            self.count = 0
            self.update_budget()
            self.old_utility = self.utility
            self.update_budget_utility()
        self.model.org_utility += self.utility  # adds organization utility to model's utility of all organizations
        self.model.total_org_utility += self.utility  # adds organization utility to model's total utility of all organizations for the calculation of the average utility for the batchrunner

        # for calculating the average compromised per step
        self.model.newly_compromised_per_step.append(self.num_compromised_new - self.num_compromised_old)
        self.compromised_per_step_aggregated += (self.num_compromised_new - self.num_compromised_old) # Organization lvl
        self.avg_compromised_per_step = self.set_avg_compromised_per_step()  # Organization lvl

        self.num_compromised_old = self.num_compromised_new
        # self.num_compromised_new = 0  # reset variable

        self.free_loading_ratio = self.get_free_loading_ratio()
        self.total_security += self.security_budget  # updating total value to get average
        self.avg_security = self.get_avg_security()

        if self.num_games_played > 0:
            self.avg_share = self.get_avg_share()

        if len(self.old_attacks_list) > 0:
            self.avg_info =  self.get_avg_known_info()

    def advance(self):
        for attack, info in self.new_attacks_list.items():
            self.old_attacks_list[attack] = self.new_attacks_list[attack].copy()
        current_time = self.model.schedule.time
        delete = []
        for attack, (_, last_update) in self.attack_awareness.items():
            if current_time - last_update > self.model.org_memory:
                delete.append(attack)
        for a in delete:
            self.clear_awareness(a)


    # <----- creating the devices and users in the subnetwork ----->
    def _create_graph(self):
        self.network = random_star_graph(self.num_devices, 0)

    def _create_devices(self):
        self.children = []
        self.users_on_subnetwork = []  # keeping track of human users on subnetwork
        self.num_users = len(self.network.nodes) - 1  # TODO num users thing
        self.model.num_users += self.num_users
        # create objects to be stored within the graph
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]
            if i == self.local_gateway_address:  # if this is the gateway
                n = NetworkDevice(address=self.address + i,
                                  parent=self,
                                  model=self.model,
                                  routing_table=routing_table)
                self.network.nodes[i]['subnetwork'] = n
            else:  # the rest of the devices are users.
                activity = random.random() / 10  # TODO parametrize

                self.network.nodes[i]['subnetwork'] = Employee(activity=activity,
                                                               address=self.address + i,
                                                               parent=self,
                                                               model=self.model,
                                                               routing_table=routing_table)

                self.users_on_subnetwork.append(self.network.nodes[i]['subnetwork'])
            self.children.append(self.network.nodes[i]['subnetwork'])


class Attackers(SubNetwork, Agent):

    def __init__(self, address, parent, model, routing_table, initial_attack_count, of='devices',
                 avg_time_to_attack_gen=0):
        SubNetwork.__init__(self, address, parent, model, routing_table, initial_attack_count, of)
        Agent.__init__(self, address, model)
        self._p_attack_generation = 1 / (avg_time_to_attack_gen + 1) if avg_time_to_attack_gen else 0.0
        self._is_generate_new_attack = False

    def step(self):
        super().step()
        self._is_generate_new_attack = random.random() < self._p_attack_generation

    def advance(self):
        if self._is_generate_new_attack:
            self._generate_new_attacker()
            self._is_generate_new_attack = False

    def _generate_new_attacker(self):
        # if VERBOSE:
        #     print("Generating new attacker!")

        new_node_local_address = self.network.number_of_nodes()  # get new address
        self.network.add_node(new_node_local_address)  # add node to graph
        self.network.add_edge(self.network.graph['gateway'], new_node_local_address)  # add edge to gateway
        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.network))  # re-compute routing table

        activity = random.random()
        attacker = Attacker(activity=activity,
                            address=self.address + new_node_local_address,
                            parent=self,
                            model=self.model,
                            routing_table=self.shortest_paths[new_node_local_address])

        # reset shortest paths for all children
        for i in range(self.network.number_of_nodes() - 1):
            self.network.nodes[i]['subnetwork'].routing_table = self.shortest_paths[i]

        self.network.nodes[new_node_local_address]['subnetwork'] = attacker  # add attacker object to graph data
        self.children.append(attacker)
        self.merge_with_master_graph()  # needed to deal with visualization
        self.model.merge_with_master_graph()  # needed to deal with visualization
        self.model.grid.G.node[attacker.master_address]['agent'] = list()  # necessary evil
        self.model.grid.place_agent(attacker, attacker.master_address)
        self.model.schedule.add(attacker)

    def _create_graph(self):
        self.network = random_star_graph(self.model.num_attackers + 1, 0)

    def _create_devices(self):
        self.children = []
        self.num_users = self.model.num_attackers  # TODO num users thing
        # create objects to be stored within the graph
        for i in range(len(self.network.nodes)):
            # company_security = get_company_security(self.num_devices)
            routing_table = self.shortest_paths[i]
            if i == self.local_gateway_address:  # if this is the gateway
                n = NetworkDevice(address=self.address + i,
                                  parent=self,
                                  model=self.model,
                                  routing_table=routing_table)
                self.network.nodes[i]['subnetwork'] = n
            else:  # the rest of the devices are users.
                activity = random.random()

                self.network.nodes[i]['subnetwork'] = Attacker(activity=activity,
                                                               address=self.address + i,
                                                               parent=self,
                                                               model=self.model,
                                                               routing_table=routing_table)

            self.children.append(self.network.nodes[i]['subnetwork'])
