from helpers import *
from agents.agents import *
from abc import ABC, abstractmethod
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
        of = 'devices'
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

        self.model.num_users += self.num_users

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


class Organization(SubNetwork):

    def _create_graph(self):
        self.network = random_star_graph(self.num_devices, 0)

    def _create_devices(self):
        self.children = []
        self.num_users = len(self.network.nodes) - 1 # TODO num users thing
        # create objects to be stored within the graph
        for i in range(len(self.network.nodes)):
            routing_table = self.shortest_paths[i]
            if i == self.local_gateway_address:  # if this is the gateway
                n = NetworkDevice(address=self.address + i,
                                        parent=self,
                                        model=self.model,
                                        routing_table=routing_table)
                self.network.nodes[i]['subnetwork'] = n
            else: # the rest of the devices are users.
                activity = random.random() / 10
                self.network.nodes[i]['subnetwork'] = User(activity=activity,
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