from mesa.agent import Agent
import helpers
import random
import numpy as np
import globalVariables

if globalVariables.GLOBAL_SEED:
    np.random.seed(globalVariables.GLOBAL_SEED_VALUE)
    random.seed(globalVariables.GLOBAL_SEED_VALUE)

class BetterAgent(Agent):
    id = 0

    def __init__(self, model):
        super().__init__(BetterAgent.id, model)
        BetterAgent.id += 1

class User(BetterAgent):

    def __init__(self, user_id, parent, model):
        super().__init__(model)
        self.user_id = user_id
        self.total_utility = 0
        self.communicate_to = []
        self.parent = parent
        self.activity = max(0, min(1, random.gauss(0.5, 1 / 6)))
        self.model.users.append(self)  # append user into model's user list

    def is_active(self):
        return random.random() < self.activity

    def step(self):
        super().step()

    def advance(self):
        pass


class Attacker(User):
    def __init__(self, attacker_id, model):
        super().__init__(attacker_id, model, model)
        self.id = attacker_id
        self.effectiveness = max(0.005, min(1, random.gauss(0.5, 1/6)))
        self.model = model

    def _generate_communicators(self):
        for org in self.model.organizations:
            if random.random() < (1-self.effectiveness):
                user = random.choice(org.users)
                if not user.parent.attacks_compromised_counts[self.id]:
                    self.communicate_to.append(user)
            else:
                random.choice(org.users)  # for randomness

    def attempt_infect(self, employee):
        if employee.is_attack_successful(attacker=self, targeted=True):
            if not employee.compromisers[self.id]:
                employee.notify_infection(self)

    def get_effectiveness(self):
        return self.effectiveness

    def step(self):
        super().step()
        self._generate_communicators()

    def advance(self):
        super().advance()

        # actually send
        for c in self.communicate_to:
            self.attempt_infect(c)
        self.communicate_to.clear()


class Employee(User):
    def __init__(self, user_id, parent, model):
        super().__init__(user_id, parent, model)
        self.compromisers = np.zeros(self.model.num_attackers, dtype=np.bool)
        self.to_clean = []

    def is_compromised(self):
        """Returns whether or not the defender is compromised"""
        return self.compromisers.any()

    def clean_specific(self, attacker_id):
        """
        Cleans the user from a specific attacker. Notifies the attacker.
        :param attacker_id: the attacker to clean
        """
        self.compromisers[attacker_id] = False
        self.parent.attacks_compromised_counts[attacker_id] -= 1

        if not self.is_compromised():  # if not compromised any more
            self.model.total_compromised -= 1
            self.parent.num_compromised_new -= 1

    def notify_infection(self, attacker):
        """
        Notifies this user that it has been infected.
        :param attacker: the attacker infecting this device
        """
        if not self.is_compromised():
            self.model.total_compromised += 1
            self.parent.num_compromised_new += 1
        self.parent.attacks_compromised_counts[attacker.id] += 1
        self.compromisers[attacker.id] = True

    def _generate_communicators(self):
        # generate list of users to talk with
        user = random.choice(self.parent.users)  # for consistent randomness when branching
        while user is self:
            user = random.choice(self.parent.users)

        if self.is_active():
            self.communicate_to.append(user)

    def step(self):
        super().step()
        self._generate_communicators()
        for attacker_id in range(self.parent.attack_awareness.shape[0]):
            if self.parent.is_aware(attacker_id) and self.compromisers[attacker_id]:
                detected = self.detect(self.model.attackers[attacker_id], targeted=True)
                if detected:
                    self.to_clean.append(attacker_id)

    def advance(self):
        super().advance()

        for c in self.to_clean:
            self.clean_specific(c)
        self.to_clean.clear()

        # talk with other users if infected
        for c in self.communicate_to:
            for attacker in self.model.attackers:
                if self.compromisers[attacker.id]:
                    if c.is_attack_successful(attacker, False):
                        if not c.compromisers[attacker.id]:
                            c.notify_infection(attacker)
                    else:
                        self.clean_specific(attacker.id)
        self.communicate_to.clear()

    def is_attack_successful(self, attacker, targeted):
        """
        Tests whether the attack was successful or not against this user
        :param attacker: the attack being performed
        :param targeted: whether or not the attack comes directly from an attacker
        :return: Boolean - whether or not the attack was successful
        """
        return not self.detect(attacker, targeted)

    def information_update(self, attacker_id):
        while self.parent.attacks_list_predetermined_idx[attacker_id] < 1000:
            next_bit = self.parent.attacks_list_predetermined[attacker_id,
                                                              self.parent.attacks_list_predetermined_idx[attacker_id]]
            if self.parent.new_attacks_list[attacker_id, next_bit]:
                self.parent.attacks_list_predetermined_idx[attacker_id] += 1
            else:
                self.parent.new_attacks_list[attacker_id, next_bit] = True
                self.parent.attacks_list_predetermined_idx[attacker_id] += 1
                break

    def make_aware(self, attacker_id, targeted, already_aware):
        if not already_aware:
            self.parent.start_incident(attacker_id)
        self.parent.attack_awareness[attacker_id, 2] += 1
        if not targeted:
            self.parent.attack_awareness[attacker_id, 1] = self.model.schedule.time

    def detect(self, attacker, targeted):
            information = self.parent.get_info(attacker.id)
            security = self.parent.security_budget
            is_aware = self.parent.is_aware(attacker.id)
            #print(information)
            if not targeted and not is_aware:  # treats aware attacks as targeted attacks
                security *= self.model.passive_detection_weight
            aggregate_security = (security + information)

            prob = helpers.get_prob_detection_v3(aggregate_security, attacker.effectiveness,
                                                 stability=self.model.detection_func_stability)
            # print(security, information, attacker.effectiveness, prob)
            if random.random() < prob:  # attack is detected, gain information
                self.information_update(attacker.id)
                self.make_aware(attacker.id, targeted, is_aware)
                return True
            else:
                return False
