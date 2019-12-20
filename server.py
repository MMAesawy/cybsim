import math

from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import UserSettableParameter
from mesa.visualization.modules import ChartModule
from mesa.visualization.modules import NetworkModule
from mesa.visualization.modules import TextElement
from model import CybCim, NetworkDevice


def network_portrayal(G):
    # The model ensures there is always 1 agent per node

    def node_color(agent):
        return '#0000FF'

    def edge_color(agent1, agent2):
        if G.get_edge_data(agent1.address, agent2.address)["active"]:
            G.get_edge_data(agent1.address, agent2.address)["active"] = False
            return '#FF0000'
        return '#909090'

    def edge_width(agent1, agent2):
        return 2

    def get_agents(source, target):
        return G.node[source]['agent'][0], G.node[target]['agent'][0]

    portrayal = dict()
    portrayal['nodes'] = [{'size': 6,
                           'color': node_color(agents[0]),
                           'tooltip': "address: %d, packets sent: %d, packets received: %d" % (agents[0].address, agents[0].packets_sent, agents[0].packets_received),
                           }
                          for (_, agents) in G.nodes.data('agent')]

    portrayal['edges'] = [{'source': source,
                           'target': target,
                           'color': edge_color(*get_agents(source, target)),
                           'width': edge_width(*get_agents(source, target)),
                           }
                          for (source, target) in G.edges]

    return portrayal


network = NetworkModule(network_portrayal, 500, 500, library='d3')



server = ModularServer(CybCim, [network], 'Computer Network')
