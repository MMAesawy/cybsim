from agents.devices import NetworkDevice
from agents.constructs import *
from collections import defaultdict
import helpers
import random



class User(NetworkDevice):
    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(address, parent, model, routing_table)
        self.activity = activity
        self.total_utility = 0
        self.communicate_to = []
        model.users.append(self)  # append user into model's user list

    def _is_active(self):
        return random.random() < self.activity

    def _generate_packet(self, destination):
        """
          Generates a packet to send.
          :return: Generated packet
          """
        packet = Packet(model=self.model, source=self, destination=destination)
        return packet

    def _generate_communicators(self):
        # generate list of users to talk with
        while len(self.parent.children) > 2 and self._is_active():  # make sure parent has more than one user
            # make sure the user is not self
            user = random.choice(self.parent.children)  # only communicate within network
            while user.address == self.address or not isinstance(user, User):
                user = random.choice(self.parent.children)
            self.communicate_to.append(user)

    def get_tooltip(self):
        return super().get_tooltip() + ("\nactivity: %.2f" % self.activity)


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
                # self.parent.attacks_list.append([c._attack_of_choice, 0.5])
                self.compromisers.pop(i)
                c.notify_clean(self)
                break

        if not self.is_compromised() and self.model.total_compromised > 0:  # if not compromised any more
            self.model.total_compromised -= 1

    def clean_all(self):
        """Cleans the user from a specific attacker. Notifies each attacker."""
        for c in self.compromisers:
            c.notify_clean(self)
        self.compromisers.clear()
        self.model.total_compromised -= 1

    def notify_infection(self, attacker):
        """
        Notifies this user that it has been infected.
        :param attacker: the attacker infecting this device
        """
        if not isinstance(attacker, GenericAttacker):
            raise ValueError("Compromiser is not an instance of GenericAttacker")
        if not self.is_compromised():
            self.model.total_compromised += 1
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

        self.compromised = []
        self.spread_to = []
        self.compromised_org = defaultdict(lambda: 0)  # storing compromised organization with the # compromised devices in each org
        self.compromised_org_count = 0
        self.model = model

    # only try to communicate with non infilterated organizations
    def _generate_communicators(self):
        # generate list of users to talk with
        while self._is_active():

            if self.compromised_org_count < (self.model.num_subnetworks - 1):
                # make sure the user is not self
                user = random.choice(self.model.users)
                while user.parent.address == self.parent.address or self.compromised_org[user.parent] > 0:
                    user = random.choice(self.model.users)

                self.communicate_to.append(user)
            else:
                if self.model.verbose:
                    print("Attacker ", self.address, " has compromised all organizations")

    def infect(self, victim):
        """
        Infects a defender WITHOUT evaluating attack success.
        Notifies the victim.
        :param victim: the victim being attacked
        """
        self.compromised.append(victim)
        self.compromised_org[victim.parent] += 1
        self.compromised_org_count += 1
        victim.notify_infection(self)

    def notify_clean(self, defender):
        """
        Notifies the attacker that the defender has been cleaned of his influence
        :param defender: the defender who was cleaned
        """
        for i, c in enumerate(self.compromised):
            if c is defender:
                self.compromised.pop(i)
                self.compromised_org[c.parent] -= 1
                self.compromised_org_count -= 1
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

        # self._strategies = ["stay", "spread", "execute"] #TODO remove
        # self._chosen_strategy = "infect"
        self._attack_of_choice = Attack(self)
        # self.utility = 0

    def get_tooltip(self):
        return super().get_tooltip() + ("\nattack effectiveness: %.2f" % self._attack_of_choice.effectiveness)

    def _generate_packet(self, destination):
        packet = super()._generate_packet(destination=destination)
        packet.add_payload(self._attack_of_choice)
        return packet

    def step(self):  # TODO rework due to strategy/decision making removal
        super().step()
        self._generate_communicators()
        for c_org, num_compromised in self.compromised_org.items():
            # # strategy_for_org = random.choice(self._strategies)
            # if strategy_for_org == "stay":
            #     self.update_stay_utility(num_compromised)
            #     c_org.update_stay_utility(num_compromised)
            # elif strategy_for_org == "execute":
            #     self.update_execute_utility(num_compromised)
            #     c_org.update_execute_utility(num_compromised)
            #     c_org.adjust_information(self._attack_of_choice) #TODO adjust
            # elif strategy_for_org == "spread":
            self.spread_to.append(c_org)
            # self.update_stay_utility(num_compromised)
            c_org.update_stay_utility(num_compromised)

    def advance(self):
        super().advance()

        # actually send packets
        for c in self.communicate_to: #will always try to spread
            packet = self._generate_packet(destination=c)
            self._send(packet)
        self.communicate_to.clear()

    def notify_victim_packet_generation(self, victim, packet):
        if victim.parent in self.spread_to:
            packet.add_payload(self._attack_of_choice)
        self.spread_to.clear()

    # def update_stay_utility(self, c):
    #     self.utility += c ** 2
    #
    # def update_execute_utility(self, c):
    #     self.utility += c

class Employee(GenericDefender):

    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(activity, address, parent, model, routing_table)

        self._security = None  # gets initialized as soon as _get_security is called.
        # do NOT use this variable directly

    def get_tooltip(self):
        return super().get_tooltip() + ("\nsecurity: %.2f" % self._get_security())

    def step(self):
        super().step()
        self._generate_communicators()
        for c in self.compromisers:
            detected = self.detect(c._attack_of_choice, targetted=False, passive=True)  # TODO: do not access private variable
            if detected:
                # self.parent.compromised_detected += 1
                self.clean_specific(c)

    def advance(self):
        super().advance()

        # actually send packets
        for c in self.communicate_to:
            packet = self._generate_packet(destination=c)
            self._send(packet)
        self.communicate_to.clear()

    def _get_security(self):
        if self._security is None:
            self._security = helpers.get_total_security(
                self.parent.security_budget, deviation_width=self.model.device_security_deviation_width)
        return self._security

    def is_attack_successful(self, attack, targetted): #detection function based chance
        if self.detect(attack, targetted):
            # attack.original_source.utility -= 0.5
            return False
        else:
            return True

    def detect(self, attack, targetted, passive=False):
        information = self.parent.attacks_list[attack]
        security = self._get_security()

        if passive:
            security *= self.model.passive_detection_weight
        elif targetted:
            security *= self.model.target_detection_weight
        else:
            security *= self.model.spread_detection_weight

        prob = helpers.get_prob_detection_v2(security, attack.effectiveness,
                                             information, info_weight=self.model.information_importance)

        if random.random() < prob:  # attack is detected, gain information
            info = self.parent.attacks_list[attack]
            self.parent.attacks_list[attack] = \
                helpers.get_new_information_detected(prob, info, w=self.model.information_gain_weight)
            return True
        else:
            return False



