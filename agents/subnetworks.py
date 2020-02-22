from agents.AttackTeam import AttackClient
from helpers import *
from agents.agents import *
from abc import ABC, abstractmethod
from mesa.agent import Agent
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
        of = self.of #'devices'
        self.children = []
        self.num_users = 0
        # create objects to be stored within the graph
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]
            if of == 'subnetworks':  # if this is a subnetwork of subnetworks:
                n = SubNetwork(address=self.address + i,
                               parent=self,
                               model=model,
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
                                                               model=model,
                                                               routing_table=routing_table)
                else:
                    self.network.nodes[i]['subnetwork'] = NetworkDevice(address=self.address + i,
                                                                        parent=self,
                                                                        model=model,
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


class Organization(SubNetwork, Agent):
    def __init__(self, address, parent, model, routing_table, num_devices, of='subnetworks'):
        SubNetwork.__init__(self, address, parent, model, routing_table, num_devices, of)
        Agent.__init__(self, address, model)

        self.blocking_list = []
        self.security_budget = 0
        self.utility = 0
        self.prob_detect_intrusion = 0.1
        self.prob_detect_stay = 0.03
        self.prob_detect_spread = 0.05 #TODO baleez figure out what to do with base probabilities and think about probabilities in general.

        model.subnetworks.append(self)

    def step(self):
        # This budget in percentage of total budget of company
        self.security_budget = random.randrange(0, 1)
        print(self.blocking_list)

    def _create_graph(self):
        self.network = random_star_graph(self.num_devices, 0)

    def _create_devices(self):
        self.children = []
        self.users_on_subnetwork = []  # keeping track of human users on subnetwork
        self.num_users = len(self.network.nodes) - 1 # TODO num users thing
        self.num_compromised = 0
        self.model.num_users += self.num_users
        # create objects to be stored within the graph
        for i in range(len(self.network.nodes)):
            company_security = get_company_security(self.num_devices)
            routing_table = self.shortest_paths[i]
            if i == self.local_gateway_address:  # if this is the gateway
                n = NetworkDevice(address=self.address + i,
                                        parent=self,
                                        model=self.model,
                                        routing_table=routing_table)
                self.network.nodes[i]['subnetwork'] = n
            else: # the rest of the devices are users.
                activity = random.random() / 10
                media_presence = random.random()  # percentage susceptable to spear phishing attacks
                type = random.randint(1, 4)  # assign a user type for each user #TODO define certain range for each type os employee
                # based on type of employee, define privileges and  percentage of users pre-existing security knowledge
                account_type, personal_security = self.define_personal_security(type)

                self.network.nodes[i]['subnetwork'] = Employee(activity=activity,
                                                                address=self.address + i,
                                                                parent=self,
                                                                model=self.model,
                                                                routing_table=routing_table,
                                                                account_type=account_type[type],
                                                                company_security=company_security,
                                                                personal_security=personal_security,
                                                                media_presence=media_presence)

                self.children.append(self.network.nodes[i]['subnetwork'])
                self.users_on_subnetwork.append(self.network.nodes[i]['subnetwork'])



    def define_personal_security(self, type):
        account_type = {1: "Front Office",
                        2: "Back Office",
                        3: "Security Team",
                        4: "Developers"}
        # assign a set of initial personal security based on each user type
        if (type == 1):
            security = random.random() * 0.3
        elif (type == 2):
            security = 0.3 + random.random() * (0.5 - 0.3)
        elif (type == 3):

            security = 0.8 + random.random() * (1 - 0.8)
        else:
            security = 0.5 + random.random() + (0.8 - 0.5)

        return account_type, security

    def advance(self):
        pass


class Attackers(SubNetwork):

    def _create_graph(self):
        self.network = random_star_graph(self.model.num_attackers+1, 0)

    def _create_devices(self):
        self.children = []
        self.num_users = self.model.num_attackers # TODO num users thing
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
            else: # the rest of the devices are users.
                activity = random.random() / 10
                # media_presence = random.random()  # percentage susceptable to spear phishing attacks
                # type = random.randint(1, 4)  # assign a user type for each user #TODO define certain range for each type os employee
                # based on type of employee, define privileges and  percentage of users pre-existing security knowledge
                # account_type, personal_security = self.define_personal_security(type)

                self.network.nodes[i]['subnetwork'] = AttackClient(activity=activity,
                                                                   address=self.address + i,
                                                                   parent=self,
                                                                   model=self.model,
                                                                   routing_table=routing_table)

                self.children.append(self.network.nodes[i]['subnetwork'])

# UNUSED
# class LocalNetwork(SubNetwork):
#
#     def _create_graph(self):
#         self.network = random_star_graph(self.num_devices, 0)
#
#     def _create_devices(self):
#         self.children = []
#         self.num_users = 0
#         # create objects to be stored within the graph
#         for i in range(len(self.network.nodes)):
#             routing_table = self.shortest_paths[i]
#             if i == self.local_gateway_address:  # if this is the gateway
#                 n = NetworkDevice(address=self.address + i,
#                                         parent=self,
#                                         model=model,
#                                         routing_table=routing_table)
#                 self.network.nodes[i]['subnetwork'] = n
#             else: # the rest of the devices are users.
#                 self.num_users = get_subnetwork_user_count(self.num_devices)
#                 activity = random.random() / 10
#                 self.network.nodes[i]['subnetwork'] = User(activity=activity,
#                                                            address=self.address + i,
#                                                            parent=self,
#                                                            model=model,
#                                                            routing_table=routing_table)
#                 self.children.append(self.network.nodes[i]['subnetwork'])
#
#
# UNUSED
# class ISP(SubNetwork):
#
#     def _create_graph(self):
#         self.network = random_mesh_graph(self.num_devices, 2)
#
#     def _create_devices(self):
#         self.children = []
#         self.num_users = 0
#         # create objects to be stored within the graph
#         for i in range(len(self.network.nodes)):
#             routing_table = self.shortest_paths[i]
#             if i == self.local_gateway_address:  # if this is the gateway
#                 n = NetworkDevice(address=self.address + i,
#                                   parent=self,
#                                   model=model,
#                                   routing_table=routing_table)
#
#             else:
#                 self.num_users = get_subnetwork_user_count(self.num_devices)
#                 activity = random.random() / 10
#                 n = User(activity=activity,
#                    address=self.address + i,
#                    parent=self,
#                    model=model,
#                    routing_table=routing_table)
#             self.network.nodes[i]['subnetwork'] = n
#             self.children.append(n)
#
# UNUSED
# class Office(SubNetwork):
#     def _create_graph(self):
#         self.network = random_star_graph(self.num_devices, 1)
#
#     def _create_devices(self):
#         self.children = []
#         self.num_users = 0
#         # create objects to be stored within the graph
#         for i in range(len(self.network.nodes)):
#             routing_table = self.shortest_paths[i]
#             if i == self.local_gateway_address:  # if this is the gateway
#                 n = NetworkDevice(address=self.address + i,
#                                   parent=self,
#                                   model=model,
#                                   routing_table=routing_table)
#             else:
#                 n = LocalNetwork(
#                        address=self.address + i,
#                        parent=self,
#                        model=model,
#                        routing_table=routing_table,
#                         num_devices=random.randint(2, 10))
#
#             self.network.nodes[i]['subnetwork'] = n
#             self.children.append(n)
#
# UNUSED
# class DataCenter(SubNetwork):
#     def _create_graph(self):
#         self.network = random_star_graph(self.num_devices, 1)
#
#     def _create_devices(self):
#         self.children = []
#         self.num_users = 0
#         # create objects to be stored within the graph
#         for i in range(len(self.network.nodes)):
#             routing_table = self.shortest_paths[i]
#             if i == self.local_gateway_address:  # if this is the gateway
#                 n = NetworkDevice(address=self.address + i,
#                                   parent=self,
#                                   model=model,
#                                   routing_table=routing_table)
#             else:
#                 n = LocalNetwork(
#                        address=self.address + i,
#                        parent=self,
#                        model=model,
#                        routing_table=routing_table,
#                         num_devices=random.randint(2, 10))
#
#             self.network.nodes[i]['subnetwork'] = n
#             self.children.append(n)
#