from model import *
from mesa.batchrunner import BatchRunner

fixed_params = {"num_subnetworks": 10,
                "num_attackers": 2}
variable_params = {"avg_time_to_new_attack": range(100, 1000, 100)}

batch_run = BatchRunner(CybCim,
                        variable_params,
                        fixed_params,
                        iterations=5,
                        max_steps=100,
                        model_reporters={
                             "Compromised Devices": get_total_compromised,
                             "Closeness": get_avg_closeness
                         })
batch_run.run_all()

run_data = batch_run.get_model_vars_dataframe()
run_data.to_csv("D:\Materials\cybsim\Result.csv")
# run_data.head()
# plt.scatter(run_data.avg_time_to_new_attack, run_data.Gini)