from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import UserSettableParameter
from mesa.visualization.modules import ChartModule
from visualization.visualization import *
from mesa.visualization.ModularVisualization import VisualizationElement

from mesa.visualization.modules import TextElement
from model import CybCim
from agents.agents import *


def network_portrayal(G):
    # The model ensures there is always 1 agent per node

    def node_color(agent):
        # p = min(255, int(agent.passing_packets / 10 * 255))
        # r = "#%s00%s" % (hex(p)[2:].zfill(2).upper(), hex(255-p)[2:].zfill(2).upper())
        # #print(r)
        # return r
        if type(agent) is Attacker:
                return "#FF0000"
        elif type(agent) is Employee:
            if not agent.is_compromised():
                return "#0000FF"
            else:
                return "#A83232"
        else:
            return "#000000"



    def edge_color(agent1, agent2):
        e = G.get_edge_data(agent1.master_address, agent2.master_address)
        if e["malicious"]:
            return '#A83232'
        elif e["active"]:
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
                               'tooltip': agents[0].get_tooltip(),
                               'id': agents[0].master_address,
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

class MyTextElement(TextElement):
    def render(self, model):
        text = "Attack Effectiveness "
        for e in model.get_attack_effectiveness():
            text += "Attack "
            text += str(e[0])
            text += ": "
            text += str("{:0.2f}".format(e[1]))
            text += " "
        text += "\nNumber of users: {}" .format(model.num_users)
        return text
        # return "Number of users: {}" .format(model.num_users), "Attacker Effectiveness " , model.get_attack_effectiveness

model_params = {
    'visualize': UserSettableParameter(param_type='checkbox', name='Enable visualization', value=True,
                                                  description='Choose whether to visualize the graph'),
    'verbose': UserSettableParameter(param_type='checkbox', name='Verbose', value=False,
                                       description='Choose whether the model is verbose (in the terminal)'),
    'information_sharing': UserSettableParameter(param_type='checkbox', name='Information Sharing', value=True,
                                       description='Choose whether or not information sharing is turned on.'),
    'interactive': UserSettableParameter(param_type='checkbox', name='Interactive graph', value=True,
                                                  description='Choose whether the graph is interactive'),
    'fisheye': UserSettableParameter(param_type='checkbox', name='Fisheye effect', value=True,
                                                      description='Choose whether a fisheye effect is enabled'),
    'subgraph_type': UserSettableParameter(param_type='checkbox', name='Subgraph of devices?', value=True,
                                                      description='Choose whether the first level of subgraphs is of devices'),
    # 'num_internet_devices': UserSettableParameter(param_type='slider', name='Number of internet devices', value=10, min_value=10, max_value=100, step=1,
    #                                               description='Choose how many internet devices to have'),
    'num_subnetworks': UserSettableParameter(param_type='slider', name='Number of subnetworks', value=10, min_value=4, max_value=50, step=1,
                                                  description='Choose how many subnetworks to have'),
    'num_attackers': UserSettableParameter(param_type='slider', name='Number of attackers', value=2, min_value=1, max_value=30, step=1,
                                                  description='Choose how many attackers to have'),
    # 'max_hops': UserSettableParameter(param_type='slider', name='Maximum hops for packets', value=5, min_value=1, max_value=20, step=1,
    #                                               description='Choose the maximum hop length for packets'),
    # 'min_capacity': UserSettableParameter(param_type='slider', name='Minimum capacity for device', value=10, min_value=10, max_value=20, step=1,
    #                                               description='Choose the minimum value for device capacity'),
    # 'max_capacity': UserSettableParameter(param_type='slider', name='Maximum capacity for device', value=20, min_value=20, max_value=30, step=1,
    #                                               description='Choose the maximum value for device capacity'),
    'device_count': UserSettableParameter(param_type='slider', name='Device count for organization', value=30, min_value=10, max_value=100, step=1,
                                                  description='Choose the number of devices for an organization'),
    # 'max_device_count': UserSettableParameter(param_type='slider', name='Maximum subnetwork device count', value=30, min_value=30, max_value=100, step=1,
    #                                               description='Choose the maximum number of devices for a subnetwork'),
    # 'avg_time_to_new_attack': UserSettableParameter(param_type='number', name='Average time for new attack', value=50,
    'avg_time_to_new_attack': UserSettableParameter(param_type='slider', name='Average time for new attack', value=500, min_value=0, max_value=1000, step=1,
                                                  description='Choose the average time for the generation of a new attack on the network'),

    # 'information_importance': UserSettableParameter(param_type='slider', name='Information importance', value=2, min_value=1, max_value=10, step=0.5,
    #                                               description='Controls the importance of information in determining probability of detection.'
    #                                                           ' Higher values means detection is harder WITHOUT information.'),
    'detection_func_stability': UserSettableParameter(param_type='slider', name='Detection Stability (1e-x)', value=3, min_value=0, max_value=5, step=1,
                                                   description='Controls the magnitude of the stability factor added to the detection probability function.'),
    'device_security_deviation_width': UserSettableParameter(param_type='slider', name='Security deviation width', value=0.25,
                                                    min_value=0, max_value=1, step=0.005,
                                                    description='Controls the deviation of devices\' security around the organization\'s security budget '),
    'information_gain_weight': UserSettableParameter(param_type='slider', name='Information gain scale', value=0.5,
                                                    min_value=0, max_value=2, step=0.01,
                                                    description='Scales the amount of information gained through a detection. Greater values means it\'s easier to gain information.'),
    'passive_detection_weight': UserSettableParameter(param_type='slider', name='Passive detection weight', value=0.125,
                                                    min_value=0, max_value=1, step=0.005,
                                                    description='Affects difficulty of passive attacker detection.'),
    'spread_detection_weight': UserSettableParameter(param_type='slider', name='Spread detection weight', value=0.25,
                                                      min_value=0, max_value=1, step=0.005,
                                                      description='Affects difficulty of spreading attacker detection.'),
    'target_detection_weight': UserSettableParameter(param_type='slider', name='Targeted detection weight', value=1.0,
                                                      min_value=0, max_value=1, step=0.005,
                                                      description='Affects difficulty of targeted attacker detection.'),
    'reciprocity': UserSettableParameter(param_type='slider',name='Reciprocity',value=2, max_value=5,min_value=1, step=0.5,
                                         description='Parameter representing how much organizations move closer or further from each other'),
    'transitivity': UserSettableParameter(param_type='slider',name='Transitivity',value=1, max_value=5,min_value=1, step=0.5,
                                         description='Parameter representing how much organizations are influenced by their cooperator\'s opinions'),
    'trust_factor': UserSettableParameter(param_type='slider',name='Trust Factor',value=2, max_value=5,min_value=1, step=0.5,
                                         description='Parameter representing how much organizations trust each other less/more after interacting'),
    'initial_trust': UserSettableParameter(param_type='slider', name='Initial trust', value=0.5, max_value=1, min_value=0,
                                          step=0.1,description='Parameter representing how much organizations are initially trusting of each other to share information'),
    'initial_closeness': UserSettableParameter(param_type='slider', name='Initial closeness', value=0.2, max_value=1, min_value=0,
                                          step=0.1,description='Parameter representing how much organizations are initially close with each other representing their likelihood to interact'),
    'sharing_factor': UserSettableParameter(param_type='slider', name='Sharing Factor', value=2, max_value=10, min_value=1,
                                          step=0.2,description='Parameter representing the amount of information gained when players both cooperate'),



}
# NOTE ABOUT WIDTHS: a width of 1000 -> full stretch across the visual elements section

network = NetworkModule(network_portrayal, canvas_width=1000)
text = VisualizationElement()

chart_1 = ChartModule([{'Label': 'Compromised Devices', 'Color': '#505050', 'PointRadius':0}], canvas_height=200)

chart_2 = ChartModule([{'Label': 'Closeness', 'Color':'#505050'}], canvas_height=200)

chart_3 = ChartModule([{'Label': 'Utility', 'Color':'#505050'}], canvas_height=200)

composite_view = TabSelectorView([chart_1, chart_2, chart_3],
                                 element_names=["Compromised Devices", "Organization Closeness","Organization Utility"],
                                 width=1000)

card_view = OrganizationCardModule()
tabbed_view = TabSelectorView([network, card_view], ["Network View", "Organization View"], width=1000)

# required in order to load visualization/modular_template.html
ModularServer.settings["template_path"] = 'visualization/'

server = ModularServer(CybCim, [tabbed_view, MyTextElement(), composite_view], 'Computer Network', model_params)
server.verbose = False
