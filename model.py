from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
from helpers import *
from agents.devices import *
from agents.agents import *


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
    def __init__(self, address, parent, model, routing_table, of='subnetworks', num_devices=25, avg_node_degree=2):
        self.address = address
        self.parent = parent
        self.model = model
        self.routing_table = routing_table
        self.of = of
        self.num_devices = num_devices
        self.current_packets = []

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
        # if destination is inside this network, consume the packet (propagate downwards)
        if self.address.is_supernetwork(packet.destination):
         self._propagate_downwards(packet)
        else:
            self._send(packet)

    def _propagate_downwards(self, packet):
        """
        Logic for 'receiving' and propagating a network packet downwards to the subnetwork's gateway.
        :param packet: the packet to propagate
        """
        self.gateway_device().route(packet)


    def _send(self, packet):
        """
        Logic for sending a network packet.
        :param packet: the packet to send
        """
        if packet not in self.current_packets:
            self.current_packets.append(packet)

        if(packet.step < packet.max_hops):
            if self.address.is_share_subnetwork(packet.destination): # device is in the local network
                dest_local_address = packet.destination[len(self.address) - 1]
                next_device_address = self.routing_table[dest_local_address][1]
                next_device = self.parent.get_subnetwork_at(next_device_address)
                packet.step += 1
            else:  # device is outside the local network, send to gateway:
                gateway_address = self.parent.gateway_local_address()
                 # if this is the gateway device:
                if self.address[-1] == gateway_address:
                    next_device = self.parent
                else:  # this is not the gateway device:
                    dest_local_address = gateway_address
                    next_device_address = self.routing_table[dest_local_address][1]
                    next_device = self.parent.get_subnetwork_at(next_device_address)
                    packet.step += 1

            print("Subnetwork %s sending packet with destination %s to device %s" %
                  (self.address, packet.destination, next_device.address))
            # only color edge if not sending packet "upwards"
            if len(self.address) == len(next_device.address):
                self._activate_edge_to(next_device)

            self.current_packets.remove(packet)
            next_device.route(packet)

        else:
            packet.stop_step = self.model.schedule.steps
            print("Packet %s going to device %s has reached maximum number of %d hops in %d steps and stopped at device %s" %
              (packet.packet_id, packet.destination, packet.max_hops, packet.step, self.address))


    def step(self):
        for n in self.network.nodes:
            n['subnetwork'].step()

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



