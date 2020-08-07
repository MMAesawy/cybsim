from agents.devices import NetworkDevice
from agents.constructs import *
from collections import defaultdict
import helpers
import random
import numpy as np
import globalVariables

if globalVariables.GLOBAL_SEED:
    np.random.seed(globalVariables.GLOBAL_SEED_VALUE)
    random.seed(globalVariables.GLOBAL_SEED_VALUE)


class User(NetworkDevice):
    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(address, parent, model, routing_table)
        self.total_utility = 0
        self.communicate_to = []
        self.parent.users.append(self)
        self.activity = max(0, min(1, random.gauss(0.5, 1 / 6)))
        model.users.append(self)  # append user into model's user list

    def _generate_packet(self, destination):
        """
          Generates a packet to send.
          :return: Generated packet
          """
        packet = Packet(model=self.model, source=self, destination=destination)
        return packet

    def _generate_communicators(self):
        # generate list of users to talk with
        if self.is_active():
            user = random.choice(self.parent.users)
            while user is self:
                user = random.choice(self.parent.users)
            self.communicate_to.append(user)
        else:  # dummy, for consistent randomness when branching
            d = random.choice(self.parent.users)
            while d is self:
                d = random.choice(self.parent.users)

    def get_tooltip(self):
        return super().get_tooltip()

    def is_active(self):
        return random.random() > self.activity


class GenericDefender(User):
    """Generic defender class"""

    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(activity, address, parent, model, routing_table)

        self.compromisers = [] # list to store all attackers that successfully infected device

    def is_compromised(self):
        """Returns whether or not the defender is compromised"""
        return len(self.compromisers) > 0

    def clean_specific(self, attacker):
        """
        Cleans the user from a specific attacker. Notifies the attacker.
        :param attacker: the attacker to clean
        """
        for i, c in enumerate(self.compromisers):
            if c is attacker:
                # self.parent.old_attacks_list.append([c._attack_of_choice, 0.5])
                self.compromisers.pop(i)
                c.notify_clean(self)
                break

        self.parent.attacks_compromised_counts[attacker.attack_of_choice] -= 1
        # if self.parent.attacks_compromised_counts[attacker.attack_of_choice] == 0:
        #     self.parent.clear_awareness(attacker.attack_of_choice)

        if not self.is_compromised():  # if not compromised any more
            self.model.total_compromised -= 1
            self.parent.num_compromised_new -= 1

    def clean_all(self):
        """Cleans the user from a specific attacker. Notifies each attacker."""
        for c in self.compromisers:
            c.notify_clean(self)
            self.parent.attacks_compromised_counts[c.attack_of_choice] -= 1
        self.compromisers.clear()
        self.model.total_compromised -= 1
        self.parent.num_compromised_new -= 1

    def notify_infection(self, attacker):
        """
        Notifies this user that it has been infected.
        :param attacker: the attacker infecting this device
        """
        if not isinstance(attacker, GenericAttacker):
            raise ValueError("Compromiser is not an instance of GenericAttacker")
        if not self.is_compromised():
            self.model.total_compromised += 1
            self.parent.num_compromised_new += 1
        self.parent.attacks_compromised_counts[attacker.attack_of_choice] += 1
        self.compromisers.append(attacker)

    def is_attack_successful(self, attack, targetted):
        """
        Tests whether the attack was successful or not against this user
        :param attack: the attack being performed
        :return: Boolean - whether or not the attack was successful
        """
        return True


    def _generate_packet(self, destination):
        """
        Generates a packet. Handles logic for packet infection and spread
        :param destination: Packet destination
        :return: Generated packet
        """
        packet = super()._generate_packet(destination=destination)
        for c in self.compromisers:
            c.notify_victim_packet_generation(victim=self,packet=packet)
        return packet

    def _receive(self, packet):
        """
        Receive a packet. Handles logic for receiving an infected packet
        :param packet: the packet
        """
        super()._receive(packet)
        packet.execute_payload()


class GenericAttacker(User):
    """Generic attacker class"""

    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(activity, address, parent, model, routing_table)
        model.attackers.append(self)
        self.attack_of_choice = Attack(self)
        self.compromised = []
        self.spread_to = []
        self.compromised_counts = np.zeros(self.model.num_subnetworks - 1, dtype=np.float)
        self.model = model

    # only try to communicate with non infilterated organizations
    def _generate_communicators(self):
        for org in self.model.organizations:
            if random.random() < (1-self.attack_of_choice.effectiveness):
                user = random.choice(org.users)
                if user not in self.compromised:
                    self.communicate_to.append(user)

    def infect(self, victim):
        """
        Infects a defender WITHOUT evaluating attack success.
        Notifies the victim.
        :param victim: the victim being attacked
        """
        self.compromised.append(victim)
        self.compromised_counts[victim.parent.id] += 1
        victim.notify_infection(self)

    def notify_clean(self, defender):
        """
        Notifies the attacker that the defender has been cleaned of his influence
        :param defender: the defender who was cleaned
        """
        for i, c in enumerate(self.compromised):
            if c is defender:
                self.compromised.pop(i)
                self.compromised_counts[c.parent.id] -= 1
                break

    def notify_victim_packet_generation(self, victim, packet):
        """
        Notifies this attacker that a victim is generating a packet. Allows the attacker to modify
        the packet and embed payloads.
        :param victim: the user who is sending the packet
        :param packet: the packet to be (potentially) modified
        """
        pass


class Attacker(GenericAttacker):

    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(activity, address, parent, model, routing_table)

    def get_tooltip(self):
        return super().get_tooltip() + ("\nattack effectiveness: %.2f" % self.attack_of_choice.effectiveness)

    def get_effectiveness(self):
        return self.attack_of_choice.effectiveness

    def _generate_packet(self, destination):
        packet = super()._generate_packet(destination=destination)
        packet.add_payload(self.attack_of_choice)
        return packet

    def step(self):  # TODO rework due to strategy/decision making removal
        super().step()
        self._generate_communicators()

    def advance(self):
        super().advance()

        # actually send packets
        for c in self.communicate_to:
            packet = self._generate_packet(destination=c)
            self._send(packet)
        self.communicate_to.clear()

    def notify_victim_packet_generation(self, victim, packet):
        packet.add_payload(self.attack_of_choice)

class Employee(GenericDefender):

    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(activity, address, parent, model, routing_table)
        self.to_clean = []
        self._security = None  # gets initialized as soon as _get_security is called.
        # do NOT use this variable directly

    def get_tooltip(self):
        return super().get_tooltip() + ("\nsecurity: %.2f" % self._get_security())

    def step(self):
        super().step()
        self._generate_communicators()
        for a in self.parent.attack_awareness.keys():
            attacker = a.original_source
            if attacker in self.compromisers:
                detected = self.detect(a, targeted=False)
                if detected:
                    self.to_clean.append(attacker)

    def advance(self):
        super().advance()

        for c in self.to_clean:
            self.clean_specific(c)
        self.to_clean.clear()

        # actually send packets
        for c in self.communicate_to:
            packet = self._generate_packet(destination=c)
            self._send(packet)
        self.communicate_to.clear()

    def _get_security(self):
        return helpers.get_total_security(
                self.parent.security_budget, deviation_width=self.model.device_security_deviation_width)

    def is_attack_successful(self, attack, targeted):
        if self.detect(attack, targeted):
            return False
        else:
            return True

    def detect(self, attack, targeted):
            information = self.parent.get_info(attack)
            security = self.parent.security_budget  #self._get_security()
            is_aware = self.parent.is_aware(attack)
            if not targeted and not is_aware:  # treats aware attacks as targeted attacks
                security *= self.model.passive_detection_weight
            aggregate_security = (security + information)
            t = attack.effectiveness
            # if is_aware:
            #     t /= self.model.attack_awareness_weight
            prob = helpers.get_prob_detection_v3(aggregate_security, t,
                                                 stability=self.model.detection_func_stability)
            # print("PROB:", prob)
            self.parent.num_attempts += 1
            if random.random() < prob:  # attack is detected, gain information
                # new_info =\
                #     helpers.get_new_information_detected(prob, information, w=self.model.information_gain_weight)
                attack_list = self.parent.new_attacks_list[attack]
                if not attack_list.all():
                    attack_list[np.random.choice(np.arange(0, 1000)[~attack_list], 1)] = True
                else:
                    np.random.choice(np.arange(0, 1000)[~attack_list], 1)  # dummy, for consistent randomness during branching
                self.parent.num_detect[attack] += 1
                if not targeted:
                    self.parent.attack_awareness[attack][1] = self.model.schedule.time
                return True
            else:
                return False
