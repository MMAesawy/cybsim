from mesa import Model
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector
import globalVariables
from agents.subnetworks import Organization
from agents.agents import Attacker
from helpers import *
import numpy as np
import time


# Data collector function for total compromised
def get_total_compromised(model):
    return model.total_compromised


# return average number of newly compromised devices for each organization
def get_avg_compromised_per_org(model):
    for i, o in enumerate(model.organizations):
        model.avg_newly_compromised_per_org[i] += model.avg_newly_compromised_per_org[i]
    return model.avg_newly_compromised_per_org / (model.schedule.time + 1)


# return the average number of newly compromised devcies among all organizations
def get_avg_newly_compromised_per_step(model):  #TODO to be called somewhere (called in batchrunner)
    return sum(model.newly_compromised_per_step) / len(model.newly_compromised_per_step)


# Data collector function for closeness between organization
def get_avg_closeness(model):
    avg = 0
    for i in range(model.num_firms):
        for j in range(i + 1, model.num_firms):
            avg += model.closeness_matrix[i, j]
    n = model.num_firms
    return avg / (n * (n-1) / 2)  # avg / n choose 2


# return number of organizations that achieve closeness >= 0.5 at teh end of run
def get_number_min_closeness(model):
    count = 0
    for i in range(model.num_firms):
        for j in range(i + 1, model.num_firms):
            if model.closeness_matrix[i, j] >= 0.5:
                count += 1
    return count


def get_avg_trust(model):
    return model.trust_matrix.mean()


def get_avg_utility(model): # TODO redundant code
    avg = model.org_utility / (model.num_firms)
    model.org_utility = 0
    return avg


def get_avg_utility_batch(model):  # TODO redundant code
    avg = model.total_org_utility / (model.num_firms)
    return avg


# returns freeloading ratio for each organization
def get_free_loading(model):
    freq = []
    for o in model.organizations:
        # freq.append(o.get_free_loading_ratio())
        freq.append(free_loading_ratio_v1(o.info_in, o.info_out))
    return freq


# return average freeloading ratio across al organizations
def get_avg_free_loading(model):
    return sum(get_free_loading(model)) / len(get_free_loading(model))


def get_avg_incident_time(model):  #TODO to be called somewhere (called in batchrunner)
    return sum(model.incident_times)/len(model.incident_times)


def get_security_per_org(model): # TODO used in subnetworks instead
    security = []
    for o in model.organizations:
        security.append(o.security_budget)
    return security

# def get_avg_security_per_org(model): # useless now
#     for i, o in enumerate(model.organizations):
#         model.avg_security_per_org[i] += o.security_budget
#     return  model.avg_security_per_org / (model.schedule.time + 1)

# returns average security among all organizations
def get_total_avg_security(model):
    total_avg_sec = 0
    for o in model.organizations:
        total_avg_sec += o.avg_security
    return total_avg_sec / len(model.organizations)
    # return sum(model.avg_security_per_org) / len(model.organizations)


class RandomCallCounter:
    def __init__(self, generator):
        self.generator = generator
        self.call_count = 0

    def __call__(self):
        self.call_count += 1
        return self.generator


class CybCim(Model):

    def __init__(self,
                 verbose=True,
                 information_sharing=True,
                 fixed_attack_effectiveness=False,
                 max_num_steps=1000,
                 num_firms=15,
                 num_attackers_initial=5,
                 device_count=30,
                 avg_time_to_new_attack=50,
                 detection_func_stability=4,
                 passive_detection_weight=0.25,
                 reciprocity=2,
                 trust_factor=2,
                 initial_closeness=0.2,
                 initial_trust=0.5,
                 security_update_interval=10,
                 org_memory=3,
                 acceptable_freeload=0.5,
                 fixed_attack_effectiveness_value=0.5,
                 global_seed=False,
                 global_seed_value=None):

        # global globalVariables.VERBOSE
        # global globalVariables.GLOBAL_SEED
        super().__init__()

        self.verbose = verbose  # adjustable parameter
        self.global_seed = global_seed  # adjustable parameter
        globalVariables.GLOBAL_SEED = global_seed
        globalVariables.VERBOSE = verbose

        self.max_num_steps = max_num_steps
        self.num_firms = num_firms  # adjustable parameter
        self.active_attacker_count = num_attackers_initial  # adjustable parameter
        self.device_count = device_count  # adjustable parameter
        self.p_attack_generation = 1 / (avg_time_to_new_attack + 1)  # adjustable parameter
        # self.information_importance = information_importance  # adjustable parameter
        self.detection_func_stability = 10**(-detection_func_stability)  # adjustable parameter
        self.passive_detection_weight = passive_detection_weight  # adjustable parameter
        self.reciprocity = reciprocity  # adjustable parameter
        self.trust_factor = trust_factor  # adjustable parameter
        self.initial_closeness = initial_closeness  # adjustable parameter
        self.initial_trust = initial_trust  # adjustable parameter
        self.information_sharing = information_sharing  # adjustable parameter
        self.security_update_interval = security_update_interval  # adjustable parameter
        self.org_memory = org_memory  # adjustable parameter
        self.acceptable_freeload = acceptable_freeload
        self.fixed_attack_effectiveness = fixed_attack_effectiveness  # adjustable parameter
        self.fixed_attack_effectiveness_value = fixed_attack_effectiveness_value  # adjustable parameter
        self.global_seed_value = global_seed_value  # adjustable parameter
        globalVariables.GLOBAL_SEED_VALUE = global_seed_value

        if globalVariables.GLOBAL_SEED:
            globalVariables.RNG = RandomCallCounter(np.random.default_rng(globalVariables.GLOBAL_SEED_VALUE))
        else:
            globalVariables.RNG = RandomCallCounter(np.random.default_rng(int(time.time())))

        self.organizations = []
        self.users = []  # keeping track of human users in all networks
        self.attackers = []

        # determine when attacks will be generated in advance:
        self.attack_generation_steps = []
        for i in range(0, int(self.max_num_steps * 0.75)):
            if globalVariables.RNG().random() < self.p_attack_generation:
                self.attack_generation_steps.append(i)
        self.attack_generation_steps.reverse()  # first attack to insert is in last place (for easy access and popping)
        self.num_attackers = self.active_attacker_count + len(self.attack_generation_steps)

        self.incident_times = []
        self.newly_compromised_per_step = []
        # self.avg_security_per_org = np.zeros(num_subnetworks - 1) # storing averages for data collection # useless
        self.avg_newly_compromised_per_org = np.zeros(num_firms)  # storing averages for data collection

        # initialize agents
        self.schedule = SimultaneousActivation(self)
        for i in range(0, self.num_firms):  # initialize orgs and add them to user list
            org = Organization(i, self)
            self.schedule.add(org)
            for user in org.users:
                self.users.append(user)
                self.schedule.add(user)
            self.organizations.append(org)
        for i in range(0, self.num_attackers):
            attacker = Attacker(i, self)
            self.attackers.append(attacker)
            if i < self.active_attacker_count:
                self.schedule.add(attacker)

        self.total_compromised = 0
        self.org_utility = 0
        self.total_org_utility = 0  # TODO byproduct of the redundant average utility function
        Organization.organization_count = 0  # reset organization count

        # TODO possibly move to own function
        # initialize a n*n matrix to store organization closeness disregarding attacker subnetwork
        self.closeness_matrix = np.full((self.num_firms, self.num_firms), self.initial_closeness, dtype=np.float)

        # initialize a n*n matrix to store organization's trust towards each other disregarding attacker subnetwork
        self.trust_matrix = np.full((self.num_firms, self.num_firms), self.initial_trust, dtype=np.float)

        # makes the trust factor between an organization and itself zero in order to avoid any average calculation errors
        np.fill_diagonal(self.trust_matrix, 0)

        # data needed for making any graphs
        self.datacollector = DataCollector(
            {
                "Compromised Devices": get_total_compromised,
                "Closeness": get_avg_closeness,
                "Average Trust": get_avg_trust,
                "Free loading": get_free_loading,
                "total avg sec": get_total_avg_security
            }
        )

        self.running = True
        self.datacollector.collect(self)

    def information_sharing_game(self):
        # TODO: implement trust factor
        for i in range(self.num_firms):
            for j in range(i + 1, self.num_firms): # only visit top matrix triangle
                r = globalVariables.RNG().random()
                if self.closeness_matrix[i, j] > r:  # will interact event
                    t1 = self.trust_matrix[i, j]
                    t2 = self.trust_matrix[j, i]
                    closeness = self.closeness_matrix[i][j]
                    # get each organization's decision to share or not based on its trust towards the other
                    r1 = self.organizations[i].share_decision(self.organizations[j], t1)
                    r2 = self.organizations[j].share_decision(self.organizations[i], t2)
                    choice = [r1, r2]
                    if sum(choice) == 2:  # both cooperate/share
                        # come closer to each other for both orgs (symmetric matrix)
                        self.closeness_matrix[i, j] = get_reciprocity(sum(choice), closeness, self.reciprocity)
                        self.closeness_matrix[j, i] = get_reciprocity(sum(choice), closeness, self.reciprocity)

                        # trust will increase for both organizations
                        self.trust_matrix[i, j] = increase_trust(t1, self.trust_factor)
                        self.trust_matrix[j, i] = increase_trust(t2, self.trust_factor)


                        # actually gain information for both organizations
                        share_info_cooperative(self.organizations[i], self.organizations[j])
                        share_info_cooperative(self.organizations[j], self.organizations[i])

                    elif sum(choice) == 0:  # both defect
                        # grow further away from each other for both orgs (symmetric matrix)
                        self.closeness_matrix[i, j] = get_reciprocity(sum(choice), closeness, self.reciprocity)
                        self.closeness_matrix[j, i] = get_reciprocity(sum(choice), closeness, self.reciprocity)

                        # trust will not be affected in this case

                    # one defects and one cooperates #no change in closeness #TODO implement different behaviour?
                    elif sum(choice) == 1:
                        if choice[0] == 1: # only org i shares
                            share_info_selfish(self.organizations[i], self.organizations[j])
                            self.trust_matrix[i, j] = decrease_trust(t1, self.trust_factor) # org i will trust org j less
                            # org j will nto update its trust

                        else: # org j shares
                            share_info_selfish(self.organizations[j], self.organizations[i])
                            self.trust_matrix[j, i] = decrease_trust(t2, self.trust_factor) # org j will trust org i less
                            #org i will not update its trust
                else:
                    globalVariables.RNG().random()  # dummy, for consistent randomness when branching
                    globalVariables.RNG().random()  # dummy, for consistent randomness when branching

    # given two organiziation indices, return their closeness
    def get_closeness(self, i, j):
        if i > j:
            j, i = i, j
        return self.closeness_matrix[i, j]

    def get_attack_effectiveness(self):
        e = []
        for i in range(len(self.attackers)):
            e.append((i + 1, self.attackers[i].get_effectiveness()))
        return e

    def step(self):
        if self.information_sharing:
            self.information_sharing_game()  # TODO: move after agent step???
        else:
            self.dummy_fun_1()  # for consistent randomness during branching

        current_step = self.schedule.time
        if self.attack_generation_steps and current_step >= self.attack_generation_steps[-1]:
            self.attack_generation_steps.pop()
            self.schedule.add(self.attackers[self.active_attacker_count])
            self.active_attacker_count += 1

        # update agents
        self.schedule.step()
        self.datacollector.collect(self)
        # print(globalVariables.RNG.call_count)
        # globalVariables.RNG.call_count = 0

    def dummy_fun_1(self):
        for i in range(self.num_firms):
            for j in range(i + 1, self.num_firms):
                globalVariables.RNG().random()
                globalVariables.RNG().random()
                globalVariables.RNG().random()

