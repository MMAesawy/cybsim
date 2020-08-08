from model import *
from agents import subnetworks
from mesa.batchrunner import BatchRunner, BatchRunnerMP
import numpy as np
import globalVariables


class BatchRunnerNew(BatchRunnerMP):
    def __init__(self, model_cls, variable_parameters=None,
                 fixed_parameters=None, iterations=1, max_steps=1000,
                 model_reporters=None, agent_reporters=None,
                 display_progress=True):
        super().__init__(model_cls, nr_processes=6, variable_parameters=variable_parameters,
                         fixed_parameters=fixed_parameters, iterations=iterations, max_steps=max_steps,
                         model_reporters=model_reporters, agent_reporters=agent_reporters,
                         display_progress=display_progress)

    def collect_agent_vars(self, model):
        """ Run reporters and collect agent-level variables. """
        agent_vars = {}
        for agent in model.organizations:
            agent_record = {}
            for var, reporter in self.agent_reporters.items():
                agent_record[var] = getattr(agent, reporter)
            agent_vars[agent.unique_id] = agent_record
        return agent_vars


def main():
    fixed_params = {
        "num_firms": 20,
        "fixed_attack_effectiveness": False,
        "global_seed": True,
        "global_seed_value": 1987,
        "reciprocity": 1,
        "initial_closeness": 0,
        "information_sharing": True,
        # "information_sharing": False,
        "verbose": False
    }

    seeds = [29233, 36213, 28448, 16157, 38804, 67989, 91932, 6015, 33792, 65966, 97525, 72606, 96381, 52185, 54486,
             80911, 14489,
             42883, 3124, 61385, 25115, 22852, 23201, 46375, 48165, 75589, 22349, 2732, 26187, 28052, 18973, 26854,
             4431, 38602, 4389, 80236,
             90884, 22236, 11460, 7905, 18348, 51153, 22630, 79033, 88405, 62153, 84849, 23375, 26388, 33618]
    variable_params = {
        # "global_seed_value": seeds
        # "information_sharing": {True, False},
        # "information_sharing": {False},
    }

    batch_run = BatchRunnerNew(CybCim,
                               variable_params,
                               fixed_params,
                               iterations=5,
                               max_steps=200,
                               model_reporters={
                                   # "Average Utility loss": get_avg_utility_batch,
                                   # "Closeness": get_avg_closeness,
                                   # "Average freeloading": get_avg_free_loading,
                                   # "Average Incident time": get_avg_incident_time,
                                   # "Average of newly compromised per step": get_avg_newly_compromised_per_step
                               },
                               agent_reporters={
                                   "Average incident time per Org.": "avg_incident_times",
                                   "Free loading per Org.": "free_loading_ratio",
                                   "Average security per Org.": "avg_security",
                                   "Avg. num. of compromised per step": "avg_compromised",
                                   "Avg. info shared per Org.": "avg_info"
                               },
                               display_progress=True)
    batch_run.run_all()

    # run_data = batch_run.get_model_vars_dataframe()
    run_data = batch_run.get_agent_vars_dataframe()
    # run_data.to_csv("D:\Materials\cybsim\_newResult.csv")
    # run_data.to_csv("Result_1.csv")
    run_data.to_csv("Result_2.csv")


if __name__ == "__main__":
    main()
