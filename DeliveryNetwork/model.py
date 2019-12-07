import math
from enum import Enum
import networkx as nx

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
from mesa.space import NetworkGrid


class State(Enum):
    FREE = 0
    OCCUPIED = 1


def number_state(model, state):
    return sum([1 for a in model.grid.get_all_cell_contents() if a.state is state])


def number_infected(model):
    return number_state(model, State.OCCUPIED)


def number_susceptible(model):
    return number_state(model, State.FREE)




class DeliveryNetwork(Model):

    def __init__(self, num_nodes=10, avg_node_degree=3, initial_packets_quantity=1, packet_delivery_chance=0.4):

        self.num_nodes = num_nodes
        prob = avg_node_degree / self.num_nodes
        self.G = nx.erdos_renyi_graph(n=self.num_nodes, p=prob)
        self.grid = NetworkGrid(self.G)
        self.schedule = RandomActivation(self)
        self.initial_packets_quantity = initial_packets_quantity if initial_packets_quantity <= num_nodes else num_nodes
        self.packet_delivery_chance = packet_delivery_chance
        self.datacollector = DataCollector({"Infected": number_infected,
                                            "Susceptible": number_susceptible})


        # Create agents
        for i, node in enumerate(self.G.nodes()):
            a = Device(i, self, State.FREE, self.packet_delivery_chance)
            self.schedule.add(a)
            # Add the agent to the node
            self.grid.place_agent(a, node)

        # Give some nodes packets to deliver
        random_sample = self.random.sample(self.G.nodes(), initial_packets_quantity)
        print(random_sample)
        occupied_nodes = self.grid.get_cell_list_contents(random_sample)
        for a in range(len(occupied_nodes)):
            # Create packets
            packet = Packet(occupied_nodes[a].unique_id, self, occupied_nodes[a].unique_id, self.random.randint(0, 9))
            occupied_nodes[a].packet = packet
            occupied_nodes[a].state = State.OCCUPIED

        self.running = True
        self.datacollector.collect(self)

    def step(self):
        self.schedule.step()
        # collect data
        self.datacollector.collect(self)

    def run_model(self, n):
        for i in range(n):
            self.step()


class Device(Agent):
    def __init__(self, unique_id, model, initial_state, packet_delivery_chance, packet=None):
        super().__init__(unique_id, model)

        self.state = initial_state
        self.packet_delivery_chance = packet_delivery_chance
        self.packet = packet

    def try_to_deliver_to_next(self, packet):
        if packet is None:
            return
        path = [agent for agent in self.model.grid.get_cell_list_contents(packet.path)]
        for a in range(len(path)):
            if a == len(path)-1:
                return
            if self.unique_id == path[a].unique_id:
                if self.random.random() < self.packet_delivery_chance:
                    path[a+1].packet = packet
                    path[a+1].state = State.OCCUPIED
                    self.packet = None
                    self.state = State.FREE

    def step(self):
        if self.state is State.OCCUPIED:
            self.try_to_deliver_to_next(self.packet)

class Packet():
    def __init__(self, packet_id, model, source, destination):
        self.packet_id = packet_id
        self.model = model
        self.source = source
        self.destination = destination
        self.path = nx.shortest_path(model.G, source, destination)
