from agents.agents import *
import random
import numpy as np
import globalVariables

if globalVariables.GLOBAL_SEED:
    np.random.seed(globalVariables.GLOBAL_SEED_VALUE)
    random.seed(globalVariables.GLOBAL_SEED_VALUE)


class Organization(BetterAgent):
    def __init__(self, org_id, model):
        super().__init__(model)

        self.id = org_id
        self.users = []
        self.old_utility = 0
        self.utility = 0
        # dictionary storing attack and known information about it, row = attack, column = info
        self.old_attacks_list = np.zeros((self.model.num_attackers, 1000), dtype=np.bool)
        # updated dictionary storing attack and known information about it, row = attack, column = info
        self.new_attacks_list = np.zeros((self.model.num_attackers, 1000), dtype=np.bool)

        # for random seeding
        self.attacks_list_predetermined = np.zeros((self.model.num_attackers, 1000), dtype=np.int)
        self.attacks_list_predetermined_idx = np.zeros(self.model.num_attackers, dtype=np.int)
        for i in range(self.model.num_attackers):
            self.attacks_list_predetermined[i] = np.arange(1000)
            np.random.shuffle(self.attacks_list_predetermined[i])

        self.attacks_list_mean = np.zeros(self.model.num_attackers)
        # to store attackers and number of devices compromised from organization
        self.attacks_compromised_counts = np.zeros(self.model.num_attackers, dtype=np.int)
        # self.org_out = np.zeros(len(model.organizations))
        self.org_out = np.zeros(self.model.num_firms)  # store the amount of info shared with other organizations

        # incident start, last update
        self.attack_awareness = np.zeros((self.model.num_attackers, 4), dtype=np.int) # inc_start, last_update, num_detected, active
        self.security_budget = max(0.005, min(1, random.gauss(0.5, 1 / 6)))
        # self.security_budget = 0.005
        self.num_compromised_new = 0  # for getting avg rate of compromised per step
        self.num_compromised_old = 0  # for getting avg rate of compromised per step
        self.count = 0
        self.risk_of_sharing = 0.3  # TODO: parametrize, possibly update in update_utility_sharing or whatever
        self.info_in = 0  # total info gained
        self.info_out = 0  # total info shared outside
        self.security_drop = min(1, max(0, random.gauss(0.75, 0.05)))
        self.acceptable_freeload = self.model.acceptable_freeload  # freeloading tolerance towards other organizations
        self.unhandled_incidents = []

        # create employees
        for i in range(0, self.model.device_count):
            self.users.append(Employee(i, self, self.model))

        # <---- Data collection ---->

        self.free_loading_ratio = 0  # variable to store freeloading ratio for each organization

        # to store changing organization security
        self.total_security = 0  # used for batch runner
        self.avg_security = 0

        self.compromised_per_step_aggregated = 0
        self.avg_newly_compromised_per_step = 0  # TODO yet to be used

        self.num_compromised = 0
        self.avg_compromised = 0

        self.incident_times = 0  # for avg incident time
        self.avg_incident_times = 0  # for avg incident time
        self.incident_times_num = 0  # for avg incident time

        self.time_with_incident = 0
        self.avg_time_with_incident = 0

        # to store times organization shares when it enters a game
        self.total_share = 0
        self.avg_share = 0
        self.num_games_played = 0

        # to store average known info
        self.avg_info = 0

        # <--- adding organization to model org array and setting unique ID --->

    def get_avg_compromised(self):
        return self.num_compromised / (self.model.schedule.time + 1)

    # returns the average information known by organization from all attacks
    def get_avg_known_info(self):
        return self.old_attacks_list[:self.model.active_attacker_count, :].mean()

    # returns average security across all time steps
    def get_avg_security(self):
        return self.total_security / (self.model.schedule.time + 1)

    # returns the freeloading ratio this organization does across all its interactions
    def get_free_loading_ratio(self):
        return self.info_in / (self.info_in + self.info_out + 1e-5)

    # returns whether or not to share information according to other party
    def share_decision(self, org2, trust):
        self.num_games_played += 1  # for data collector
        info_out = self.org_out[org2.id]  # org1 out (org1_info_out)
        info_in = org2.org_out[self.id]  # org1 in (org2_info_out)
        if info_out > info_in:  # decreases probability to share
            share = random.random() < trust * min(1, self.acceptable_freeload + (info_in / info_out))
        else:
            share = random.random() < trust
        if share:
            self.total_share += 1  # for data collector
        return share

    # returns average times an organization shared across all its played games
    def get_avg_share(self):
        return self.total_share / self.num_games_played

    def update_budget(self):
        ratio = 0
        unhandled_attack_count = 0
        current_time = self.model.schedule.time
        for i in range(self.attack_awareness.shape[0]):
            if self.attack_awareness[i, 3]:
                incident_time = current_time - self.attack_awareness[i, 0]  # how long incident lasted so far
                if incident_time > self.model.org_memory:
                    ratio += self.attack_awareness[i, 2] / len(self.users) / incident_time
                    unhandled_attack_count += 1
        for inc in self.unhandled_incidents:
            ratio += float(inc[2] / len(self.users) / (inc[1]-inc[0]))
            unhandled_attack_count += 1
        self.unhandled_incidents.clear()

        if unhandled_attack_count:  # a security incident happened and wasn't handled in time
            ratio /= unhandled_attack_count
            self.security_budget += (1 - self.security_budget) * ratio
        else:
            self.security_budget *= self.security_drop
        self.security_budget = max(0.005, min(1.0, self.security_budget))

    def update_incident_times(self, attack_id):
        current_time = self.model.schedule.time
        incident_time = current_time - self.attack_awareness[attack_id, 0] - self.model.org_memory
        if incident_time > self.model.org_memory:
            assert self.attack_awareness[attack_id, 3] == 1
            self.unhandled_incidents.append(self.attack_awareness[attack_id, :].tolist())
        self.model.incident_times.append(incident_time)
        self.incident_times += incident_time  # for avg incident time

    def set_avg_incident_time(self):  # for avg incident time
        return self.incident_times / self.incident_times_num

    def set_avg_time_with_incident(self):
        return self.time_with_incident / (self.model.schedule.time + 1)

    def start_incident(self, attack_id):
        self.attack_awareness[attack_id] = [self.model.schedule.time, self.model.schedule.time, 0, 1]

    # remove attacker from awareness array if handled in acceptable time based on org memory
    def clear_awareness(self, attack_id):
        self.update_incident_times(attack_id)
        self.incident_times_num += 1  # for avg incident time
        self.avg_incident_times = self.set_avg_incident_time()
        self.attack_awareness[attack_id] = [0, 0, 0, 0]

    # return boolean if organization is aware of specific attack
    def is_aware(self, attack_id):
        return self.attack_awareness[attack_id, 3] == 1

    def get_percent_compromised(self, attack_id=None):
        """Returns the percentage of users compromised for each attack (or the total if `attack` is None)"""
        if attack_id is not None:
            return self.attacks_compromised_counts[attack_id] / len(self.users)
        return self.num_compromised_old / len(self.users)

    def set_avg_compromised_per_step(self):
        return self.compromised_per_step_aggregated / (self.model.schedule.time + 1)

    # return amount of information known given a specific attack
    def get_info(self, attack_id):
        return self.attacks_list_mean[attack_id]

    def step(self):
        self.count += 1
        # organization updates its security budget every n steps based on previous step utility in order to improve its utility
        if self.count == self.model.security_update_interval:
            self.count = 0
            self.update_budget()
        self.model.org_utility += self.utility  # adds organization utility to model's utility of all organizations
        self.model.total_org_utility += self.utility  # adds organization utility to model's total utility of all organizations for the calculation of the average utility for the batchrunner

        # for calculating the average compromised per step
        self.model.newly_compromised_per_step.append(self.num_compromised_new - self.num_compromised_old)
        self.compromised_per_step_aggregated += (self.num_compromised_new - self.num_compromised_old)  # Organization lvl
        self.avg_newly_compromised_per_step = self.set_avg_compromised_per_step()  # Organization lvl

        self.num_compromised_old = self.num_compromised_new
        # self.num_compromised_new = 0  # reset variable

        self.free_loading_ratio = self.get_free_loading_ratio() # update freeloading ratio variable every step

        # <-- updating security variables to get security averages --->
        self.total_security += self.security_budget
        self.avg_security = self.get_avg_security()

        # <--- updating average number of times shared when playing a game --->
        if self.num_games_played > 0:
            self.avg_share = self.get_avg_share()

        # <--- updating average information known about all attacks --->
        if len(self.old_attacks_list) > 0:
            self.avg_info = self.get_avg_known_info()

        if len(self.attack_awareness) > 0:
            self.time_with_incident += 1

        self.avg_time_with_incident = self.set_avg_time_with_incident()

        self.avg_compromised = self.get_avg_compromised()



    def advance(self):
        self.old_attacks_list = self.new_attacks_list.copy()
        self.attacks_list_mean = self.old_attacks_list.mean(axis=1)
        current_time = self.model.schedule.time

        for attack_id in range(self.attack_awareness.shape[0]):
            if self.is_aware(attack_id) and current_time - self.attack_awareness[attack_id, 1] > self.model.org_memory:
                self.clear_awareness(attack_id)
