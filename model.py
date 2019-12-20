from mesa import Agent, Model
from mesa.space import NetworkGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import networkx as nx
import random

class AddressServer():
    def __init__(self, initial=0):
        self.next_address = initial


    def serve(self):
        self.next_address += 1
        return self.next_address - 1


class CybCim(Model):

    def __init__(self, num_devices = 25, avg_node_degree=2):
        super().__init__()

        self.num_devices = num_devices
        prob = avg_node_degree / self.num_devices

        self.G = nx.erdos_renyi_graph(n=self.num_devices, p=prob, directed=False)
        self.shortest_paths = dict(nx.all_pairs_shortest_path(self.G))
        #print([len(x) for x in self.shortest_paths.values()])
        self.grid = NetworkGrid(self.G)
        self.schedule = RandomActivation(self)
        self.total_packets_received = 0
        self.datacollector = DataCollector(
            {"packets_received": "total_packets_received"},
        )

        self.address_server = AddressServer()

        self.devices = []
        for i, node in enumerate(self.G.nodes()):
            routing_table = self.shortest_paths[node]
            a = NetworkDevice(i,#self.address_server.serve(),
                              self,
                              routing_table)
            self.devices.append(a)
            self.grid.place_agent(a, node)
            self.schedule.add(a)
        for edge in self.G.edges(data=True):
            edge[2]["active"] = False
        self.running = True
        self.datacollector.collect(self)

    def step(self):
        self.schedule.step()

class NetworkDevice(Agent):

    def __init__(self, address, model, routing_table):
        super().__init__(address, model)

        self.address = address
        self.routing_table = routing_table
        self.packets_received = 0
        self.packets_sent = 0




    def route(self, destination_address, message):
        if self.address == destination_address:
            self.packets_received += 1
            self.model.total_packets_received += 1
            print("Device %d received packet: %s" % (self.address, message))
            return


        #print(self.routing_table)
        if destination_address not in self.routing_table:
            print("Cannot connect to %d, packet discarded." % destination_address)
            return

        self.packets_sent += 1
        next_device = self.routing_table[destination_address][1]
        self.model.G.get_edge_data(self.address, next_device)["active"] = True

        print("Sending packet to device %d" % next_device)
        self.model.devices[next_device].route(destination_address, message)

    def step(self):
        r = random.random()
        #print(r)
        if r < 0.05:
            dest = random.choice([x.address for x in self.model.devices])
            print("Device %d attempting to message %d" % (self.address, dest))
            msg = "Dear %d, ur m0m is fAt. Sinc, %d" % (dest, self.address)
            self.route(dest, msg)
