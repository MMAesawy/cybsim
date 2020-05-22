from agents.devices import NetworkDevice
from agents.constructs import *
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
        while self._is_active():
            # make sure the user is not self
            user = random.choice(self.model.users)
            while user == self:
                user = random.choice(self.model.users)

            self.communicate_to.append(user)


class GenericDefender(User):
    """Generic defender class"""

    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(activity, address, parent, model, routing_table)

        self.compromisers = []

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
                self.parent.blocking_list.append(c)
                self.compromisers.pop(i)
                c.notify_clean(self)
                break
        if not self.is_compromised(): # if not compromised any more
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
        self.compromisers.append(attacker)
        self.model.total_compromised += 1

    def is_attack_successful(self, attack): # TODO
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
            c.notify_victim_packet_generation(packet=packet)
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

    def infect(self, victim):
        """
        Infects a defender WITHOUT evaluating attack success.
        Notifies the victim.
        :param victim: the victim being attacked
        """
        self.compromised.append(victim)
        victim.notify_infection(self)

    def notify_clean(self, defender):
        """
        Notifies the attacker that the defender has been cleaned of his influence
        :param defender: the defender who was cleaned
        """
        for i, c in enumerate(self.compromised):
            if c is defender:
                self.compromised.pop(i)
                break

    def notify_victim_packet_generation(self, packet):
        """
        Notifies this attacker that a victim is generating a packet. Allows the attacker to modify
        the packet and embed payloads.
        :param packet: the packet to be (potentially) modified
        """
        pass


class Attacker(GenericAttacker):

    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(activity, address, parent, model, routing_table)

        self._strategies = ["stay", "spread", "infect"] #TODO execute strategy to get payoff
        self._chosen_strategy = random.choice(self._strategies)
        self._attack_of_choice = self._generate_new_attack()

    def _generate_new_attack(self):
        self.total_utility = self.total_utility * 0.8
        return Attack(original_source=self)

    def _generate_packet(self, destination):
        packet = super()._generate_packet(destination=destination)
        packet.add_payload(self._attack_of_choice)
        return packet

    def step(self):
        super().step()
        self._chosen_strategy = random.choice(self._strategies)

        # generate list of users to talk with
        if self._chosen_strategy == "infect":
            self._generate_communicators()

    def advance(self):
        super().advance()

        # actually send packets
        for c in self.communicate_to:
            packet = self._generate_packet(destination=c)
            self._send(packet)
        self.communicate_to.clear()

    def notify_victim_packet_generation(self, packet):
        #if self._chosen_strategy == "spread":
        packet.add_payload(self._attack_of_choice)


class Employee(GenericDefender):

    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(activity, address, parent, model, routing_table)
        self.type = random.choice(["Front Office", "Back Office", "Security Team", "Developers"])  # TODO set restrictions on number of specific type.
        self.security = self.define_security(self.type)


    def step(self):
        super().step()
        self._generate_communicators()

    def advance(self):
        super().advance()

        # actually send packets
        for c in self.communicate_to:
            packet = self._generate_packet(destination=c)
            self._send(packet)
        self.communicate_to.clear()

    def define_security(self, type):
        # assign a set of initial personal security based on each user type
        if (type == "Front Office"):
            security = random.random() * 0.3
        elif (type == "Back Office"):
            security = 0.3 + random.random() * (0.5 - 0.3)
        elif (type == "Security Team"):

            security = 0.8 + random.random() * (1 - 0.8)
        elif (type == "Developers"):
            security = 0.5 + random.random() + (0.8 - 0.5)
        else:
            security = 0

        return ((security * 0.6) + (self.parent.company_security * 0.4)) / 2

    def is_attack_successful(self, attack):
        if attack.effectiveness > self.security:
            return True
        else:
            return False

    def detect(self, effectiveness, attack_type):
        if attack_type in self.parent.blocking_list:
            isKnown = 1
        else:
            isKnown = 0
        securityBudget = self.parent.security_budget
        prob = ((1 - effectiveness) + isKnown + securityBudget + self.parent.num_compromised / self.parent.num_users) / 4
        detected = False
        # if random.random() < prob: