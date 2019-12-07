import math

from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import UserSettableParameter
from mesa.visualization.modules import ChartModule
from mesa.visualization.modules import NetworkModule
from mesa.visualization.modules import TextElement
from .model import DeliveryNetwork, State, number_infected


def network_portrayal(G):
    # The model ensures there is always 1 agent per node

    def node_color(agent):
        return {
            State.OCCUPIED: '#FF0000',
            State.FREE: '#008000'
        }.get(agent.state, '#808080')

    def edge_color(agent1, agent2):
        return '#e8e8e8'

    def edge_width(agent1, agent2):
        return 2

    def get_agents(source, target):
        return G.node[source]['agent'][0], G.node[target]['agent'][0]

    def if_occupied(agent):
        if agent.state == State.OCCUPIED:
            return agent.packet.packet_id
        else:
            return 'x'

    portrayal = dict()
    portrayal['nodes'] = [{'size': 6,
                           'color': node_color(agents[0]),
                           'tooltip': "id: {}<br>state: {}<br>p-id: {}".format(agents[0].unique_id,
                                                                               agents[0].state.name,
                                                                               if_occupied(agents[0])),
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
chart = ChartModule([{'Label': 'Occupied', 'Color': '#FF0000'},
                     {'Label': 'Free', 'Color': '#008000'}])


class MyTextElement(TextElement):
    def render(self, model):
        packet_text = str(number_infected(model))

        return "<br>Occupied: {}".format(packet_text)


model_params = {
    'num_nodes': UserSettableParameter('slider', 'Number of agents', 30, 10, 100, 1,
                                       description='Choose how many agents to include in the model'),
    'avg_node_degree': UserSettableParameter('slider', 'Avg Node Degree', 6, 3, 8, 1,
                                             description='Avg Node Degree'),
    'initial_packets_quantity': UserSettableParameter('slider', 'Initial Packets Quantity', 3, 1, 10, 1,
                                                   description='Initial Packets Quantity'),
    'packet_delivery_chance': UserSettableParameter('slider', 'Packet Delivery Chance', 0.4, 0.0, 1.0, 0.1,
                                                 description='Probability that the packet will be delivered to it''s next Device'),

}

server = ModularServer(DeliveryNetwork, [network, MyTextElement(), chart], 'Delivery Network Model', model_params)
server.port = 8521
