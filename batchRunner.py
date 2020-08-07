from model import *
from agents import subnetworks
from mesa.batchrunner import BatchRunner
import numpy as np
import random
import globalVariables

if globalVariables.GLOBAL_SEED:
    np.random.seed(globalVariables.GLOBAL_SEED_VALUE)
    random.seed(globalVariables.GLOBAL_SEED_VALUE)


class BatchRunnerNew(BatchRunner):
    def __init__(self, model_cls, variable_parameters=None,
                 fixed_parameters=None, iterations=1, max_steps=1000,
                 model_reporters=None, agent_reporters=None,
                 display_progress=True):
        BatchRunner.__init__(self, model_cls, variable_parameters,
                             fixed_parameters, iterations, max_steps,
                             model_reporters, agent_reporters,
                             display_progress)

    def collect_agent_vars(self, model):
        """ Run reporters and collect agent-level variables. """
        agent_vars = {}
        for agent in model.organizations:
            agent_record = {}
            for var, reporter in self.agent_reporters.items():
                agent_record[var] = getattr(agent, reporter)
            agent_vars[agent.unique_id] = agent_record
        return agent_vars


fixed_params = {
    "num_subnetworks": 10,
    "fixed_attack_effectiveness": False,
    "global_seed": True,
    "global_seed_value": 1987,
    # "reciprocity": 1,
    # "initial_closeness": 0,
    "information_sharing": False,
    "verbose": False
}

variable_params = {
    # "information_sharing": {True, False},
    # "information_sharing": {False},
}

batch_run = BatchRunnerNew(CybCim,
                           variable_params,
                           fixed_params,
                           iterations=5,
                           max_steps=200,
                           model_reporters={
                               "Average Utility loss": get_avg_utility_batch,
                               "Closeness": get_avg_closeness,
                               "Average freeloading": get_avg_free_loading,
                               "Average Incident time": get_avg_incident_time,
                               "Average of newly compromised per step": get_avg_newly_compromised_per_step
                           },
                           agent_reporters={
                               # "Average incident time per Org.": "avg_incident_times",
                               # "Free loading per Org.": "free_loading_ratio",
                               # "Average security per Org.": "avg_security",
                               # "Avg. num. of compromised per step": "avg_compromised_per_step",
                               # "Avg known info": "avg_info",
                               # "times with incidents": "time_with_incident"
                           },
                           display_progress=True)
batch_run.run_all()

run_data = batch_run.get_model_vars_dataframe()
# run_data = batch_run.get_agent_vars_dataframe()
# run_data.to_csv("D:\Materials\cybsim\Result.csv")
# run_data.to_csv("Result_1.csv")
run_data.to_csv("Result_2.csv")

# run_data.head()
# plt.scatter(run_data.avg_time_to_new_attack, run_data.Gini)
