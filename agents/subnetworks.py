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

        self._create_graph()

        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.network))
        self.local_gateway_address = self.network.graph['gateway']

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
    def __init__(self, address, parent, model, routing_table, num_devices, of='subnetworks'):
        SubNetwork.__init__(self, address, parent, model, routing_table, num_devices, of)
        Agent.__init__(self, address, model)
        self.utility_buffer = 0
        self.attacks_list = defaultdict(lambda: 0)
        self.security_budget = max(0, min(1, random.gauss(0.5, 1 / 6)))
        self.utility = 0
        self.count = 0
        self.risk_of_sharing = 0.3  # TODO: parametrize, possibly update in update_utility_sharing or whatever
        self.model = model
        model.subnetworks.append(self)

    #TODO fix this
    def step(self):

        self.count += 1
        print("before:", self.security_budget)
        print(self.count)
        print("utility:", self.utility)
        # organization updates its security budget every n steps based on previous step utility in order to improve its utility
        if self.count == 10:  # TODO parametrize
            self.count = 0
            self.update_budget()
            self.update_budget_utility()
        self.utility_buffer = self.utility + self.security_budget #remove effect of security budget
        print("after:" , self.security_budget)
        self.model.org_utility += self.utility # adds organization utility to model's utility of all organizations

    def advance(self):
        pass

    def share_decision(self, trust):
        """Returns whether or not to share information according to other party."""
        # TODO make decision based on trust factor, pass other org object instead of just closeness
        return random.random() < trust

    def adjust_information(self, attack):
        self.attacks_list[attack] = 1

    def update_budget(self):  # TODO: decision making?
        self.utility += self.security_budget #remove effect of security budget
        utility_drop = self.utility_buffer - self.utility
        print("Drop", utility_drop)
        if utility_drop >= 0.5: # TODO possibly increase threshold
            self.security_budget += 0.1
        else:
            self.security_budget -= 0.1
        self.security_budget = max(0, min(1, self.security_budget))
        # self.security_budget = max(0, min(1, random.gauss(0.5, 1 / 6)))

    def update_budget_utility(self):
        self.utility -= self.security_budget ** 2

    def update_execute_utility(self, num_compromised): # TODO possibly useless now?
        self.utility -= num_compromised

    def update_stay_utility(self, num_compromised): # TODO possibly useless now?
        self.utility -= num_compromised ** 2

    def update_information_utility(self):
        self.utility -= self.risk_of_sharing

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
        model.subnetworks.append(self)

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
