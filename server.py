import math

from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import UserSettableParameter
from mesa.visualization.modules import ChartModule
from mesa.visualization.modules import PieChartModule
from visualization.visualization import NetworkModule
from mesa.visualization.ModularVisualization import VisualizationElement

from mesa.visualization.modules import TextElement
from model import CybCim
from agents.AttackTeam import AttackClient
from agents.devices import NetworkDevice
from agents.agents import Employee


def network_portrayal(G):
    # The model ensures there is always 1 agent per node

    def node_color(agent):
        # p = min(255, int(agent.passing_packets / 10 * 255))
        # r = "#%s00%s" % (hex(p)[2:].zfill(2).upper(), hex(255-p)[2:].zfill(2).upper())
        # #print(r)
        # return r
        if type(agent) is AttackClient:
                return "#A83232"
        elif type(agent) is Employee:
            if (agent.state == "Safe"):
                return "#0000FF"
            else:
                return "#FFC0CB"
        else:
            return "#000000"



    def edge_color(agent1, agent2):
        e = G.get_edge_data(agent1.master_address, agent2.master_address)
        if type(agent1) is AttackClient:
            if e["active"]:
                return '#A83232'
        else:
            if e["active"]:
                return '#0000FF'
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
    if G.graph['visualize']:
        portrayal['nodes'] = [{'size': 6,
                               'color': node_color(agents[0]),
                               'tooltip': "address: %s, packets sent: %d, packets received: %d Network type: %s" % (agents[0].address,
                                                                                                   agents[0].packets_sent,
                                                                                                   agents[0].packets_received,
                                                                                                   agents[0].type),
                               'id': i,
                               }
                              for i, (_, agents) in enumerate(G.nodes.data('agent'))]

        portrayal['edges'] = [{'source': source,
                               'target': target,
                               'color': edge_color(*get_agents(source, target)),
                               'width': edge_width(*get_agents(source, target)),
                               'id':i,
                               }
                              for i, (source, target) in enumerate(G.edges)]
        portrayal['interactive'] = 1 if G.graph["interactive"] else 0
        portrayal['fisheye'] = 1 if G.graph["fisheye"] else 0
    return portrayal

chart = ChartModule([{'Label': 'Packets Received', 'Color': '#008000'},
                     {'Label': 'Packets Dropped', 'Color': '#FF0000'}])

chart2 = ChartModule([{'Label': 'Compromised Devices', 'Color': '#ff4c4c'}])

pie = PieChartModule([{'Label': 'Safe Devices', 'Color': '#4ca64c'},
                     {'Label': 'Compromised Devices', 'Color': '#ff4c4c'}],
                     canvas_width=730)

class MyTextElement(TextElement):
    def render(self, model):
        return "Number of devices: {}  Number of users: {}" .format(len(model.devices), model.num_users)

model_params = {
    'visualize': UserSettableParameter(param_type='checkbox', name='Enable visualization', value=True,
                                                  description='Choose whether to visualize the graph'),
    'verbose': UserSettableParameter(param_type='checkbox', name='Verbose', value=True,
                                       description='Choose whether the model is verbose (in the terminal)'),
    'interactive': UserSettableParameter(param_type='checkbox', name='Interactive graph', value=True,
                                                  description='Choose whether the graph is interactive'),
    'fisheye': UserSettableParameter(param_type='checkbox', name='Fisheye effect', value=True,
                                                      description='Choose whether a fisheye effect is enabled'),
    'subgraph_type': UserSettableParameter(param_type='checkbox', name='Subgraph of devices?', value=True,
                                                      description='Choose whether the first level of subgraphs is of devices'),
    'num_internet_devices': UserSettableParameter(param_type='slider', name='Number of internet devices', value=100, min_value=50, max_value=100, step=1,
                                                  description='Choose how many internet devices to have'),
    'num_subnetworks': UserSettableParameter(param_type='slider', name='Number of subnetworks', value=5, min_value=5, max_value=100, step=1,
                                                  description='Choose how many subnetworks to have'),
    'max_hops': UserSettableParameter(param_type='slider', name='Maximum hops for packets', value=20, min_value=1, max_value=20, step=1,
                                                  description='Choose the maximum hop length for packets'),
    'min_capacity': UserSettableParameter(param_type='slider', name='Minimum capacity for device', value=20, min_value=10, max_value=20, step=1,
                                                  description='Choose the minimum value for device capacity'),
    'max_capacity': UserSettableParameter(param_type='slider', name='Maximum capacity for device', value=30, min_value=20, max_value=30, step=1,
                                                  description='Choose the maximum value for device capacity'),
    'min_device_count': UserSettableParameter(param_type='slider', name='Minimum subnetwork device count', value=5, min_value=5, max_value=25, step=1,
                                                  description='Choose the minimum number of devices for a subnetwork'),
    'max_device_count': UserSettableParameter(param_type='slider', name='Maximum subnetwork device count', value=25, min_value=25, max_value=50, step=1,
                                                  description='Choose the maximum number of devices for a subnetwork'),


}
network = NetworkModule(network_portrayal, 500, 730)
text = VisualizationElement()




server = ModularServer(CybCim, [network, MyTextElement(), chart, chart2, pie], 'Computer Network',   model_params)
