from model import *
from mesa.batchrunner import BatchRunner

fixed_params = {"fixed_attack_effectiveness": True,
                "information_sharing": True,
                "verbose": False}
variable_params = {}

batch_run = BatchRunner(CybCim,
                        variable_params,
                        fixed_params,
                        iterations=1,
                        max_steps=2000,
                        model_reporters={
                            "Average Utility loss": get_avg_utility_batch,
                            "Closeness": get_avg_closeness,
                            "Average freeloading": get_avg_free_loading,
                            "Average Incident time": get_avg_incident_time,
                            "Average of newly compromised per step": get_avg_newly_compromised_per_step
                        })
batch_run.run_all()

run_data = batch_run.get_model_vars_dataframe()
# run_data.to_csv("D:\Materials\cybsim\Result.csv")
run_data.to_csv("Result.csv")
# run_data.head()
# plt.scatter(run_data.avg_time_to_new_attack, run_data.Gini)
