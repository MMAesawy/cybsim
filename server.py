from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import UserSettableParameter
from mesa.visualization.modules import ChartModule
from visualization.visualization import *
from mesa.visualization.ModularVisualization import VisualizationElement

from mesa.visualization.modules import TextElement
from model import CybCim
from agents.agents import *

model_params = {
    'verbose': UserSettableParameter(param_type='checkbox', name='Verbose', value=False,
                                       description='Choose whether the model is verbose (in the terminal)'),
    'information_sharing': UserSettableParameter(param_type='checkbox', name='Information Sharing', value=True,
                                       description='Choose whether or not information sharing is turned on.'),
    'fixed_attack_effectiveness': UserSettableParameter(param_type='checkbox', name='Fixed attack effectiveness', value=False,
                                                      description='Choose whether the attack effectiveness across all attacks are the same value'),
    'global_seed': UserSettableParameter(param_type='checkbox', name='Use global seed?', value=False,
                                                      description='Choose whether or not to use a global seed for the random number generators'),
    "global_seed_value": UserSettableParameter(param_type='number', name='Global seed\'s value', value=1987,
                                               description='Set the value of the global seed'),
    'num_firms': UserSettableParameter(param_type='slider', name='Number of subnetworks', value=10, min_value=4, max_value=50, step=1,
                                                  description='Choose how many subnetworks to have'),
    'num_attackers_initial': UserSettableParameter(param_type='slider', name='Number of attackers', value=2, min_value=1, max_value=30, step=1,
                                                  description='Choose how many attackers to have'),
    'device_count': UserSettableParameter(param_type='slider', name='Device count for organization', value=30, min_value=10, max_value=100, step=1,
                                                  description='Choose the number of devices for an organization'),
    'avg_time_to_new_attack': UserSettableParameter(param_type='slider', name='Average time for new attack', value=50, min_value=0, max_value=500, step=1,
                                                  description='Choose the average time for the generation of a new attack on the network'),
    'passive_detection_weight': UserSettableParameter(param_type='slider', name='Passive detection weight', value=0.25,
                                                    min_value=0.01, max_value=1, step=0.005,
                                                    description='Affects difficulty of passive attacker detection.'),
    'reciprocity': UserSettableParameter(param_type='slider',name='Reciprocity',value=2, max_value=5,min_value=1, step=0.5,
                                         description='Parameter representing how much organizations move closer or further from each other'),
    'trust_factor': UserSettableParameter(param_type='slider',name='Trust Factor',value=2, max_value=5,min_value=1, step=0.5,
                                         description='Parameter representing how much organizations trust each other less/more after interacting'),
    'initial_trust': UserSettableParameter(param_type='slider', name='Initial trust', value=0.5, max_value=1, min_value=0,
                                          step=0.1,description='Parameter representing how much organizations are initially trusting of each other to share information'),
    'initial_closeness': UserSettableParameter(param_type='slider', name='Initial closeness', value=0.2, max_value=1, min_value=0,
                                          step=0.1,description='Parameter representing how much organizations are initially close with each other representing their likelihood to interact'),
    'security_update_interval': UserSettableParameter(param_type='slider', name='Security Update Interval', value=10, max_value=50, min_value=1,
                                          step=1,description='Parameter representing interval at which organizations update their security'),
    'org_memory': UserSettableParameter(param_type='slider', name='Organization Memory', value=3, max_value=20, min_value=1,
                                          step=1,description='Parameter representing organization attack awareness memory'),
    'acceptable_freeload': UserSettableParameter(param_type='slider', name='Acceptable Freeload', value=0.5, max_value=1, min_value=0,
                                          step=0.1,description='Parameter representing organization acceptable freeloading tolerance'),
    'fixed_attack_effectiveness_value': UserSettableParameter(param_type='slider', name='Fixed attack effectiveness value', value=0.5, max_value=1, min_value=0,
                                          step=0.05,description='Parameter representing the value of the fixed attack effectiveness value across all attacks')
}
# NOTE ABOUT WIDTHS: a width of 1000 -> full stretch across the visual elements section

text = VisualizationElement()

chart_1 = ChartModule([{'Label': 'Compromised Devices', 'Color': '#505050', 'PointRadius':0}], canvas_height=200)

chart_2 = ChartModule([{'Label': 'Closeness', 'Color':'#505050'}], canvas_height=200)

chart_3 = ChartModule([{'Label': 'Average Trust', 'Color':'#505050'}], canvas_height=200)

composite_view = TabSelectorView([chart_1, chart_2, chart_3],
                                 element_names=["Compromised Devices", "Organization Closeness", " Average Trust"],
                                 width=1000)

card_view = OrganizationCardModule()

# required in order to load visualization/modular_template.html
ModularServer.settings["template_path"] = 'visualization/'

server = ModularServer(CybCim, [card_view, composite_view], 'Computer Network', model_params)
server.verbose = False
