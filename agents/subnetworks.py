from agents.agents import *
import numpy as np
from collections import defaultdict


class Firm(BetterAgent):
    @staticmethod
    def get_probability_detection(aggregate_security, attacker_effectiveness, stability=1e-5):
        """
        1D function that computes the probability of detection.
        :param aggregate_security: Array containing the aggregate security of the firm against each attacker
        :param attacker_effectiveness: Array containing the effectiveness of each attacker
        :param stability: Value to be added to denominator for numerical stability
        :return: Array containing the probability that each attacker is detected.
        """
        return aggregate_security / (aggregate_security + attacker_effectiveness + stability)

    def __init__(self, org_id, model):
        super().__init__(model)

        self.id = org_id
        self.devices = []

        # matrix storing attack and known information about it, row = attack, column = info bit
        self.old_info_array = np.zeros((self.model.num_attackers, 1000), dtype=np.bool)
        # updated matrix storing attack and known information about it, row = attack, column = info bit
        self.new_info_array = np.zeros((self.model.num_attackers, 1000), dtype=np.bool)

        # for random seeding
        # stores a sequence of bits to reveal for each attacker
        self.info_array_predetermined = np.zeros((self.model.num_attackers, 1000), dtype=np.int)
        self.info_array_predetermined_next = np.zeros(self.model.num_attackers, dtype=np.int)
        for i in range(self.model.num_attackers):
            self.info_array_predetermined[i] = np.arange(1000)
            self.model.RNG().shuffle(self.info_array_predetermined[i])

        self.info_proportions = np.zeros(self.model.num_attackers)
        # to store attackers and number of devices compromised from organization
        self.attacks_compromised_counts = np.zeros(self.model.num_attackers, dtype=np.int)
        # self.org_out = np.zeros(len(model.firms))
        self.org_out = np.zeros(self.model.num_firms)  # store the amount of info shared with other firms

        self.attack_awareness = np.zeros(self.model.num_attackers, dtype=np.bool)
        self.detection_counts = np.zeros(self.model.num_attackers, dtype=np.int)
        self.security_budget = max(0.005, min(1, self.model.RNG().normal(0.5, 1 / 6)))
        self.security_change = 0
        self.num_detects_new = 0

        self.info_in = 0
        self.info_out = 0

        self.data = defaultdict(lambda: [])
        self.create_step_datapoints()

        self.prob_detection_elevated = np.zeros(self.model.num_attackers)
        self.prob_detection_normal = np.zeros(self.model.num_attackers)

        self.step_count = 0
        self.security_drop = min(1, max(0, self.model.RNG().normal(0.75, 0.05)))
        self.acceptable_freeload = self.model.acceptable_freeload  # freeloading tolerance towards other firms

        # create employees
        for i in range(0, self.model.device_count):
            self.devices.append(Device(i, self, self.model))

    # returns whether or not to share information according to other party
    def get_share_decision(self, other_firm_id, random_value=None):
        info_out = self.model.info_exchange_matrix[self.id, other_firm_id]
        info_in = self.model.info_exchange_matrix[other_firm_id, self.id]
        trust = self.model.trust_matrix[self.id, other_firm_id]

        if random_value is None:
            random_value = self.model.RNG().random()

        if info_out > info_in:  # decreases probability to share
            share = random_value < trust * min(1, self.acceptable_freeload + (info_in / info_out))
        else:
            share = random_value < trust
        return share

    def get_aggregate_security_array(self, elevated):
        """
        Computes and returns an array of aggregate security values against all attackers.
        :param elevated: Whether or not it's a `elevated` detection.
        :return: Returns a 1D array of aggregate securities for each attacker.
        """
        agg_sec = np.ones(self.model.num_attackers) * (self.security_budget + 1) * self.info_proportions #+ 1e-4
        if elevated:
            agg_sec += self.security_budget
        else:
            agg_sec += 1e-4
        return agg_sec

    def update_prob_detection_arrays(self):
        """Compute and update the probability of detection arrays for all attackers."""
        agg_sec_elevated = self.get_aggregate_security_array(elevated=True)
        agg_sec_normal = self.get_aggregate_security_array(elevated=False)

        self.prob_detection_elevated = Firm.get_probability_detection(agg_sec_elevated,
                                                                      self.model.attacker_effectiveness_array)
        self.prob_detection_normal = Firm.get_probability_detection(agg_sec_normal,
                                                                    self.model.attacker_effectiveness_array)

    def update_budget(self):
        """Compute and update the security budget of the firm."""
        total_detections = self.detection_counts.max()
        if total_detections:  # a security incident happened and wasn't handled in time
            self.security_change += (1 - self.security_budget) * (total_detections/self.model.device_count)
        self.security_budget += self.security_change
        self.security_budget = max(0.005, min(1.0, self.security_budget))
        self.security_change = 0
        self.detection_counts = np.zeros(self.model.num_attackers, dtype=np.int)

    def information_update(self, attacker_id):
        """Gain new information for a specific attacker."""
        # loop over indices till the next available one is found
        while self.info_array_predetermined_next[attacker_id] < 1000:
            next_bit_idx = self.info_array_predetermined[attacker_id, self.info_array_predetermined_next[attacker_id]]
            self.info_array_predetermined_next[attacker_id] += 1

            if not self.new_info_array[attacker_id, next_bit_idx]:  # if next bit is not already revealed
                self.new_info_array[attacker_id, next_bit_idx] = True  # reveal the bit
                break

    def device_infected_listener(self, device_id, attacker_id):  # TODO
        self.attacks_compromised_counts[attacker_id] += 1
        self.data["infection_count"][-1] += 1

    def attacker_detected_listener(self, device_id, attacker_id):  # TODO
        self.attack_awareness[attacker_id] = True
        self.attacks_compromised_counts[attacker_id] -= 1
        self.attack_awareness[attacker_id] = (self.attacks_compromised_counts[attacker_id] != 0)
        self.detection_counts[attacker_id] += 1
        self.data["detection_count"][-1] += 1

    # return boolean if organization is aware of specific attack
    def is_aware(self, attack_id):
        return self.attack_awareness[attack_id]

    def get_percent_compromised(self, attack_id=None):
        """Returns the percentage of devices compromised for each attack (or the total if `attack` is None)"""
        return self.get_total_compromised(attack_id) / len(self.devices)

    def get_total_compromised(self, attack_id=None):
        """Returns the total count of devices compromised for each attack (or the total if `attack` is None)"""
        if attack_id is not None:
            return self.attacks_compromised_counts[attack_id]
        return sum([d.is_compromised() for d in self.devices])

    # return amount of information known given a specific attack
    def get_info_proportion(self, attack_id):
        return self.info_proportions[attack_id]

    def create_step_datapoints(self):
        self.data["detection_count"].append(0)
        self.data["info_in"].append(0)
        self.data["info_out"].append(0)
        self.data["infection_count"].append(0)
        self.data["security_budget"].append(self.security_budget)
        self.data["info_total"].append(self.old_info_array.sum())
        self.data["compromised_count"].append(self.get_total_compromised())
        # self.data["num_devices"].append(len(self.devices))
        # self.data["num_attackers"].append(len(self.model.num_attackers))

    def step(self):
        self.create_step_datapoints()
        self.update_prob_detection_arrays()

        if self.num_detects_new == 0:
            self.security_change -= (1-self.security_drop) * self.security_budget / self.model.security_update_interval
        self.num_detects_new = 0

    def advance(self):
        # organization updates its security budget every n steps
        # based on previous step utility in order to improve its utility
        self.step_count += 1
        if self.step_count == self.model.security_update_interval:
            self.step_count = 0
            self.update_budget()

        self.old_info_array = self.new_info_array.copy()
        self.info_proportions = self.old_info_array.mean(axis=1)
