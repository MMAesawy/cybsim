from mesa.agent import Agent
import numpy as np


class BetterAgent(Agent):
    id = 0

    def __init__(self, model):
        """
            Simple improvement upon agent as it automatically deals with setting the global agent ID.

            Global agent ID is required for some Mesa functions but are not used within the model, instead
            opting for separate ID pools for each agent type.
        """
        super().__init__(BetterAgent.id, model)
        BetterAgent.id += 1


class User(BetterAgent):
    def __init__(self, user_id, parent, model):
        super().__init__(model)
        self.user_id = user_id
        self.total_utility = 0
        self.communicate_to = []
        self.parent = parent
        self.activity = max(0, min(1, self.model.RNG().normal(0.5, 1 / 6)))
#        self.model.users.append(self)  # append user into model's user list

    def is_active(self):
        return self.model.RNG().random() < self.activity

    def step(self):
        super().step()

    def advance(self):
        pass


class Attacker(User):
    def __init__(self, attacker_id, model):
        super().__init__(attacker_id, model, model)
        self.id = attacker_id
        self.effectiveness = max(0.005, min(1, self.model.RNG().normal(0.5, 1/6)))
        self.model = model
        self.predetermined_detection = np.zeros(self.model.num_firms, dtype=np.bool)

    def _generate_communicators(self):
        for firm in self.model.firms:
            user = self.model.RNG().choice(firm.devices)
            if self.model.RNG().random() < (1-self.effectiveness):
                if not user.parent.attacks_compromised_counts[self.id]:
                    self.communicate_to.append(user)

    def attempt_infect(self, device):
        if self.predetermined_detection[device.parent.id]:
            device.parent.information_update(self.id)
        else:
            if not device.compromisers[self.id]:
                device.get_infected(self.id)

    def get_effectiveness(self):
        return self.effectiveness

    def step(self):
        super().step()
        for i in range(self.predetermined_detection.shape[0]):
            self.predetermined_detection[i] = self.model.firms[i].devices[0].detection_trial_opt(self, True)
        self._generate_communicators()

    def advance(self):
        super().advance()

        # actually send
        for c in self.communicate_to:
            self.attempt_infect(c)
        self.communicate_to.clear()


class Device(User):
    def __init__(self, user_id, parent, model):
        super().__init__(user_id, parent, model)
        self.compromisers = np.zeros(self.model.num_attackers, dtype=np.bool)
        self.to_clean = np.zeros(self.model.num_attackers, dtype=np.bool)
        self.to_compromise = np.zeros(self.model.num_attackers, dtype=np.bool)

    def is_compromised(self):
        """Returns whether or not the defender is compromised"""
        return self.compromisers.any()

    def clean_specific(self, attacker_id):
        """
        Cleans the user from a specific attacker. Notifies the attacker.
        :param attacker_id: the attacker to clean
        """
        if self.compromisers[attacker_id]:
            self.parent.attacker_detected_listener(device_id=self.id, attacker_id=attacker_id)
            self.compromisers[attacker_id] = False

    def get_infected(self, attacker_id):
        """
        Notifies this user that it has been infected.
        :param attacker_id: id of the attacker infecting this device
        """
        if not self.compromisers[attacker_id]:
            self.parent.device_infected_listener(device_id=self.id, attacker_id=attacker_id)
            self.compromisers[attacker_id] = True

    def _generate_communicators(self):
        """
        Generate list of devices for this device to talk with. Devices are added to self.communicate_to.
        :return:
        """
        # choose a random device id.
        # zero not included in range as to not select self. see code below
        user_id = self.model.RNG().choice(np.arange(1, len(self.parent.devices)))
        if user_id <= self.id:
            user_id -= 1  # adjust id pool as to not select self.

        self.communicate_to.append(self.parent.devices[user_id])

    def step(self):
        super().step()
        self._generate_communicators()

        # perform a detection trial for each attacker
        for attacker_id in range(self.model.num_attackers):
            detected = self.detection_trial_opt(self.model.attackers[attacker_id], targeted=False)
            if self.parent.is_aware(attacker_id) and self.compromisers[attacker_id]:
                if detected:
                    self.to_clean[attacker_id] = True
                    self.parent.information_update(attacker_id)

        # talk with other devices if infected
        active = self.is_active()
        for attacker_id in range(self.model.num_attackers):
            already_detected = self.to_clean[attacker_id]
            for other_device in self.communicate_to:  # typically one other device
                detected = self.detection_trial_opt(self.model.attackers[attacker_id], targeted=False)
                # if this device is compromised
                # and the attacker is not already detected in this device
                # and the other device isn't already compromised by this attacker
                # #EDIT nevermind, causes attacks to never get detected once everyone in the firm is infected
                if active and self.compromisers[attacker_id] and not already_detected: #\
                        #and not other_device.compromisers[attacker_id]:
                    if detected:
                        self.to_clean[attacker_id] = True
                        self.parent.information_update(attacker_id)
                    else:
                        other_device.to_compromise[attacker_id] = True

    def advance(self):
        super().advance()

        for attacker_id in range(self.model.num_attackers):
            # cleaning takes precedence over infection.
            if self.to_clean[attacker_id]:
                self.clean_specific(attacker_id)
            elif self.to_compromise[attacker_id]:
                self.get_infected(attacker_id)

        self.to_clean = np.zeros(self.model.num_attackers, dtype=np.bool)
        self.to_compromise = np.zeros(self.model.num_attackers, dtype=np.bool)
        self.communicate_to.clear()

    def detection_trial_opt(self, attacker, targeted):
        """
        Attempts to detect the attacker by running an attack detection trial. Optimized version that makes
        use of the firm's precomputed probability of detection arrays.
        :param attacker: The attacker object (not attacker ID)
        :param targeted: Whether or not the attack is `targeted` i.e. comes directly from the attacker.
        :return: Boolean representing whether or not the attacker was detected.
        """
        r = self.model.RNG().random()
        if targeted or self.parent.is_aware(attacker.id):  # elevated state
            return r < self.parent.prob_detection_elevated[attacker.id]
        return r < self.parent.prob_detection_normal[attacker.id]  # non-elevated state

    def detection_trial_full(self, attacker, targeted):
        """
        Attempts to detect the attacker by running an attack detection trial.
        :param attacker: The attacker object (not attacker ID)
        :param targeted: Whether or not the attack is `targeted` i.e. comes directly from the attacker.
        :return: Boolean representing whether or not the attacker was detected.
        """
        information = self.parent.get_info_proportion(attacker.id)
        security = self.parent.security_budget
        elevated_state = targeted or self.parent.is_aware(attacker.id)

        if elevated_state:
            aggregate_security = security + information + security * information
        else:
            aggregate_security = information + security * information + 0.001

        prob_detect = aggregate_security / (aggregate_security + attacker.effectiveness + 1e-5)

        return self.model.RNG().random() < prob_detect

