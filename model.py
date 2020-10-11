from mesa import Model
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector
from agents.subnetworks import Firm
from agents.agents import Attacker
import numpy as np
import time


class RandomCallCounter:
    def __init__(self, generator):
        self.generator = generator
        self.call_count = 0

    def __call__(self):
        self.call_count += 1
        return self.generator


class CybCim(Model):

    def __init__(self,
                 verbose=False,
                 information_sharing=True,
                 # fixed_attack_effectiveness=False,
                 max_num_steps=1000,
                 num_firms=12,
                 num_attackers_initial=5,
                 num_attackers_total = 10,
                 device_count=30,
                 # avg_time_to_new_attack=50,
                 # detection_func_stability=4,
                 # passive_detection_weight=0.25,
                 reciprocity=2,
                 trust_factor=2,
                 initial_closeness=0.2,
                 initial_trust=0.5,
                 security_update_interval=10,
                 # org_memory=3,
                 acceptable_freeload=0.5,
                 # fixed_attack_effectiveness_value=0.5,
                 random_seed=0):

        # global globalVariables.VERBOSE
        # global globalVariables.GLOBAL_SEED
        super().__init__()

        self.verbose = verbose  # adjustable parameter

        self.max_num_steps = max_num_steps
        self.num_firms = num_firms  # adjustable parameter
        self.active_attacker_count = num_attackers_initial  # adjustable parameter
        self.device_count = device_count  # adjustable parameter
        self.closeness_reciprocity = reciprocity  # adjustable parameter
        self.trust_reciprocity = trust_factor  # adjustable parameter
        self.initial_closeness = initial_closeness  # adjustable parameter
        self.initial_trust = initial_trust  # adjustable parameter
        self.information_sharing = information_sharing  # adjustable parameter
        self.security_update_interval = security_update_interval  # adjustable parameter
        self.acceptable_freeload = acceptable_freeload  # adjustable parameter

        if not random_seed:
            random_seed = int(time.time())
        self.RNG = RandomCallCounter(np.random.default_rng(random_seed))

        self.firms = []
        self.devices = []
        self.attackers = []

        # determine when attacks will be generated in advance:
        entering_attackers = num_attackers_total - num_attackers_initial
        self.attack_generation_steps = self.RNG().choice(np.arange(0, int(self.max_num_steps * 0.75)),
                                                                    size=entering_attackers, replace=False).tolist()
        self.attack_generation_steps.sort(reverse=True) # first attack to insert is in last place (for easy access and popping)
        # print(self.attack_generation_steps)
        self.num_attackers = num_attackers_total  # adjustable parameter

        self.incident_times = []
        self.newly_compromised_per_step = []
        # self.avg_security_per_org = np.zeros(num_subnetworks - 1) # storing averages for data collection # useless
        self.avg_newly_compromised_per_org = np.zeros(num_firms)  # storing averages for data collection

        # initialize agents
        self.schedule = SimultaneousActivation(self)
        for i in range(0, self.num_firms):  # initialize orgs and add them to scheduler
            org = Firm(i, self)
            self.schedule.add(org)
            self.firms.append(org)
        for org in self.firms:  # add devices in each organization to scheduler
            for user in org.devices:
                self.devices.append(user)
                self.schedule.add(user)

        self.attacker_effectiveness_array = np.zeros(self.num_attackers)  # used for optimization
        for i in range(0, self.num_attackers):  # initialize attackers and add each attacker to scheduler
            attacker = Attacker(i, self)
            self.attackers.append(attacker)
            if i < self.active_attacker_count:
                self.schedule.add(attacker)
            self.attacker_effectiveness_array[i] = attacker.effectiveness

        self.total_compromised = 0
        self.org_utility = 0
        Firm.organization_count = 0  # reset organization count

        # initialize a n*n matrix to store organization closeness disregarding attacker subnetwork
        self.closeness_matrix = np.full((self.num_firms, self.num_firms), self.initial_closeness, dtype=np.float)
        # initialize a n*n matrix to store organization's trust towards each other disregarding attacker subnetwork
        self.trust_matrix = np.full((self.num_firms, self.num_firms), self.initial_trust, dtype=np.float)
        # initialize a n*n information exchange matrix.
        # self.info_exchange_matrix[i][j] signifies the number of info bits org i has given to org j
        self.info_exchange_matrix = np.zeros((self.num_firms, self.num_firms), dtype=np.int)

        # makes the trust factor between an organization and itself zero in order to avoid any average calculation errors
        np.fill_diagonal(self.trust_matrix, 0)
        np.fill_diagonal(self.closeness_matrix, 0)

        self._init_data_collector()

        self.running = True
        self.datacollector.collect(self)

    def _init_data_collector(self):
        # data needed for making any graphs
        self.datacollector = DataCollector(
            model_reporters={
                # "Compromised Devices": get_total_compromised,
                # "Closeness":           get_avg_closeness,
                # "Average Trust":       get_avg_trust,
                # "Free loading":        get_free_loading,
                # "total avg sec":       get_total_avg_security,
                # "num attackers":       get_num_attackers
            },
            agent_reporters={}
        )

    def _increase_closeness(self, old_closeness, reciprocity):
        return 1 - ((1 - old_closeness) / reciprocity)

    def _decrease_closeness(self, old_closeness, reciprocity):
        return old_closeness / reciprocity

    def _increase_trust(self, old_trust, reciprocity):
        return 1 - ((1 - old_trust) / reciprocity)

    def _decrease_trust(self, old_trust, reciprocity):
        return old_trust / reciprocity

    def _information_sharing_routine(self):
        for i in range(self.num_firms):
            for j in range(i + 1, self.num_firms):  # only do pairwise firms
                self._play_information_sharing_game(i, j)

    def _play_information_sharing_game(self, firm1_id, firm2_id):
        rand_play = self.RNG().random()
        rand_f1_share = self.RNG().random()
        rand_f2_share = self.RNG().random()

        prob_interaction = self.closeness_matrix[firm1_id, firm2_id]
        if rand_play < prob_interaction:  # play the sharing game
            firm1_share = self.firms[firm1_id].get_share_decision(firm2_id, rand_f1_share)
            firm2_share = self.firms[firm2_id].get_share_decision(firm1_id, rand_f2_share)

            if firm1_share and firm2_share:  # cooperative game
                self._cooperative_game(firm1_id, firm2_id)
            elif firm1_share:  # selfish game, firm 1 shares
                self._selfish_game(sharing_firm_id=firm1_id, selfish_firm_id=firm2_id)
            elif firm2_share:  # selfish game, firm 2 shares
                self._selfish_game(sharing_firm_id=firm2_id, selfish_firm_id=firm1_id)
            else:  # no game
                self._no_game(firm1_id, firm2_id)

    def _cooperative_game(self, firm1_id, firm2_id):
        # update closeness
        old_closeness = self.closeness_matrix[firm1_id, firm2_id]
        new_closeness = self._increase_closeness(old_closeness, self.closeness_reciprocity)
        self.closeness_matrix[firm1_id, firm2_id] = new_closeness
        self.closeness_matrix[firm2_id, firm1_id] = new_closeness

        # update trust
        old_trust_ij = self.trust_matrix[firm1_id, firm2_id]
        old_trust_ji = self.trust_matrix[firm2_id, firm1_id]
        self.trust_matrix[firm1_id, firm2_id] = self._increase_trust(old_trust_ij, self.trust_reciprocity)
        self.trust_matrix[firm2_id, firm1_id] = self._increase_trust(old_trust_ji, self.trust_reciprocity)

        # actually share information
        firm1 = self.firms[firm1_id]
        firm2 = self.firms[firm2_id]

        old_info_f1 = firm1.old_info_array
        old_info_f2 = firm2.old_info_array
        new_info = np.logical_or(old_info_f1, old_info_f2)

        new_info_total_f1 = np.logical_xor(new_info, old_info_f1).sum()
        new_info_total_f2 = np.logical_xor(new_info, old_info_f2).sum()
        firm1.data["info_in"][-1] += new_info_total_f1
        firm1.data["info_out"][-1] += new_info_total_f2
        firm2.data["info_in"][-1] += new_info_total_f2
        firm2.data["info_out"][-1] += new_info_total_f1
        self.info_exchange_matrix[firm1_id, firm2_id] += new_info_total_f2
        self.info_exchange_matrix[firm2_id, firm1_id] += new_info_total_f1

        firm1.new_info_array = np.logical_or(new_info, firm1.new_info_array)
        firm2.new_info_array = np.logical_or(new_info, firm2.new_info_array)

    def _selfish_game(self, sharing_firm_id, selfish_firm_id):
        # closeness is not modified in selfish games
        # update trust
        old_trust_ij = self.trust_matrix[sharing_firm_id, selfish_firm_id]
        self.trust_matrix[sharing_firm_id, selfish_firm_id] = self._decrease_trust(old_trust_ij, self.trust_reciprocity)

        # actually share information
        sharing_firm = self.firms[sharing_firm_id]
        selfish_firm = self.firms[selfish_firm_id]

        old_info_sharing = sharing_firm.old_info_array
        old_info_selfish = selfish_firm.old_info_array
        new_info = np.logical_or(old_info_sharing, old_info_selfish)

        # TODO: different strategies for defining information shared to selfish firm
        # info_shared_total = np.logical_xor(new_info, old_info_selfish).sum(axis=1)
        # info_shared_total = np.logical_or(new_info, old_info_selfish).sum(axis=1)
        info_shared_total = old_info_sharing.sum()
        sharing_firm.data["info_out"][-1] += info_shared_total
        selfish_firm.data["info_in"][-1] += info_shared_total
        self.info_exchange_matrix[sharing_firm_id, selfish_firm_id] = info_shared_total

        selfish_firm.new_info_array = np.logical_or(new_info, selfish_firm.new_info_array)

    def _no_game(self, firm1_id, firm2_id):
        # update closeness
        old_closeness = self.closeness_matrix[firm1_id, firm2_id]
        new_closeness = self._decrease_closeness(old_closeness, self.closeness_reciprocity)
        self.closeness_matrix[firm1_id, firm2_id] = new_closeness
        self.closeness_matrix[firm2_id, firm1_id] = new_closeness

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
        # return [(i+1, a.get_effectiveness()) for i, a in enumerate(self.attackers)]

    def _activate_next_attacker(self):
        self.attack_generation_steps.pop()
        self.schedule.add(self.attackers[self.active_attacker_count])
        self.active_attacker_count += 1

    def step(self):
        self._information_sharing_routine()

        current_step = self.schedule.steps
        if self.attack_generation_steps and current_step >= self.attack_generation_steps[-1]:
            self._activate_next_attacker()

        # update agents
        self.schedule.step()
        self.datacollector.collect(self)
        print(self.RNG.call_count)
        self.RNG.call_count = 0

