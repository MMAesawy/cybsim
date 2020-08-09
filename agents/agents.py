from mesa.agent import Agent
import helpers
import numpy as np
import globalVariables


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
        self.activity = max(0, min(1, globalVariables.RNG().normal(0.5, 1 / 6)))
        self.model.users.append(self)  # append user into model's user list

    def is_active(self):
        return globalVariables.RNG().random() < self.activity

    def step(self):
        super().step()

    def advance(self):
        pass


class Attacker(User):
    def __init__(self, attacker_id, model):
        super().__init__(attacker_id, model, model)
        self.id = attacker_id
        self.effectiveness = max(0.005, min(1, globalVariables.RNG().normal(0.5, 1/6)))
        self.model = model
        self.predetermined_detection = np.zeros(self.model.num_firms, dtype=np.bool)

    def _generate_communicators(self):
        for org in self.model.organizations:
            if globalVariables.RNG().random() < (1-self.effectiveness):
                user = globalVariables.RNG().choice(org.users)
                if not user.parent.attacks_compromised_counts[self.id]:
                    self.communicate_to.append(user)
            else:
                globalVariables.RNG().choice(org.users)  # for randomness

    def attempt_infect(self, employee):
        if self.predetermined_detection[employee.parent.id]:
            employee.information_update(self.id)
            if employee.compromisers[self.id]:
                employee.clean_specific(self.id)
        else:
            if not employee.compromisers[self.id]:
                employee.notify_infection(self)

    def get_effectiveness(self):
        return self.effectiveness

    def step(self):
        super().step()
        for i in range(self.predetermined_detection.shape[0]):
            self.predetermined_detection[i] = self.model.organizations[i].users[0].detect(self, True)
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
        if self.parent.attacks_compromised_counts[attacker_id] == 0:
            self.parent.attack_awareness[attacker_id] = False

        if not self.is_compromised():  # if not compromised any more
            self.model.total_compromised -= 1
            self.parent.num_compromised_new -= 1
            self.parent.num_compromised -= 1

    def notify_infection(self, attacker):
        """
        Notifies this user that it has been infected.
        :param attacker: the attacker infecting this device
        """
        if not self.is_compromised():
            self.model.total_compromised += 1
            self.parent.num_compromised_new += 1
            self.parent.num_compromised += 1
        self.parent.attacks_compromised_counts[attacker.id] += 1
        self.compromisers[attacker.id] = True

    def _generate_communicators(self):
        # generate list of users to talk with
        user = globalVariables.RNG().choice(self.parent.users)  # for consistent randomness when branching
        while user is self:
            user = globalVariables.RNG().choice(self.parent.users)

        if self.is_active():
            self.communicate_to.append(user)

    def step(self):
        super().step()
        self._generate_communicators()
        for attacker_id in range(self.parent.attack_awareness.shape[0]):
            detected = self.detect(self.model.attackers[attacker_id], targeted=False)
            if self.parent.is_aware(attacker_id) and self.compromisers[attacker_id]:
                if detected:
                    self.information_update(attacker_id)
                    self.make_aware(attacker_id)
                    self.to_clean.append(attacker_id)

    def advance(self):
        super().advance()

        for c in self.to_clean:
            self.clean_specific(c)
        self.to_clean.clear()

        # talk with other users if infected
        for c in self.communicate_to:
            for attacker in self.model.attackers:
                detected = c.detect(attacker, False)
                if self.compromisers[attacker.id]:
                    if detected:
                        self.information_update(attacker.id)
                        self.make_aware(attacker.id)
                        self.clean_specific(attacker.id)
                    else:
                        if not c.compromisers[attacker.id]:
                            c.notify_infection(attacker)
        self.communicate_to.clear()

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

    def make_aware(self, attacker_id):
        self.parent.attack_awareness[attacker_id] = True
        self.parent.detection_counts[attacker_id] += 1
        self.parent.num_detects_new += 1

    def detect(self, attacker, targeted):
        information = self.parent.get_info(attacker.id)
        security = self.parent.security_budget
        is_aware = self.parent.is_aware(attacker.id)
        #print(information)
        if not targeted and not is_aware:  # treats aware attacks as targeted attacks
            aggregate_security = (security + information + security*information)
        else:
            aggregate_security = information + 0.001

        prob = helpers.get_prob_detection_v3(aggregate_security, attacker.effectiveness,
                                             stability=self.model.detection_func_stability)
        # print(security, information, attacker.effectiveness, prob)
        return globalVariables.RNG().random() < prob  # attack is detected, gain information

