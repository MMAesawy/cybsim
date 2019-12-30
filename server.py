import math

from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import UserSettableParameter
from mesa.visualization.modules import ChartModule
from mesa.visualization.modules import NetworkModule
from mesa.visualization.ModularVisualization import VisualizationElement

from mesa.visualization.modules import TextElement
from model import CybCim


def network_portrayal(G):
    # The model ensures there is always 1 agent per node

    def node_color(agent):
        return '#0000FF'

    def edge_color(agent1, agent2):
        e = G.get_edge_data(agent1.master_address, agent2.master_address)
        if e["active"]:
            return '#FF0000'
        # else:
        #     e = G.get_edge_data(agent2.model_address, agent1.model_address)
        #     if e["active"]:
        #         e["active"] = False
        #         return '#FF0000'
        return '#909090'

    def edge_width(agent1, agent2):
        e = G.get_edge_data(agent1.master_address, agent2.master_address)
        if e["active"]:
            return 2
        else:
            return 2

    def get_agents(source, target):
        return G.node[source]['agent'][0], G.node[target]['agent'][0]

    portrayal = dict()
    portrayal['nodes'] = [{'size': 6,
                           'color': node_color(agents[0]),
                           'tooltip': "address: %s, packets sent: %d, packets received: %d" % (agents[0].address, agents[0].packets_sent, agents[0].packets_received),
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
text = VisualizationElement()




server = ModularServer(CybCim, [network], 'Computer Network')
