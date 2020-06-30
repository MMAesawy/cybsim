from agents.devices import NetworkDevice
from agents.constructs import *
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
        while self._is_active():
            # make sure the user is not self
            user = random.choice(self.model.users)
            while user == self:
                user = random.choice(self.model.users)

            self.communicate_to.append(user)

    def get_tooltip(self):
        return super().get_tooltip() + ("\nactivity: %.2f" % self.activity)


class GenericDefender(User):
    """Generic defender class"""

    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(activity, address, parent, model, routing_table)

        self.compromisers = []

    def is_compromised(self):
        """Returns whether or not the defender is compromised"""
        return len(self.compromisers) > 0

    def clean_specific(self, attacker): #TODO find a better way to access the attack of choice #unsed for now
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
        if not self.is_compromised() and self.model.total_compromised > 0: # if not compromised any more
            self.model.total_compromised -= 1

    def clean_all(self): #unsed for now.
        """Cleans the user from a specific attacker. Notifies each attacker."""
        for c in self.compromisers:
            c.notify_clean(self)
        self.compromisers.clear()
        self.model.total_compromised -= 1

    def notify_infection(self, attacker): #TODO send organization object to attacker or number of children
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

        self._strategies = ["stay", "spread", "execute", "infect"] #TODO execute strategy to get payoff
        self._stay_risk = random.uniform(0, 0.2)
        self._spread_risk = random.uniform(0.2, 0.5)
        self._execute_risk = random.uniform(0.5, 1)
        self._chosen_strategy = "infect"
        self._attack_of_choice = Attack(self)
        self.utility = 0

    def get_tooltip(self):
        return super().get_tooltip() + ("\nattack effectiveness: %.2f" % self._attack_of_choice.effectiveness)

    def _generate_packet(self, destination):
        packet = super()._generate_packet(destination=destination)
        packet.add_payload(self._attack_of_choice)
        return packet

    def step(self):
        super().step()
        # generate list of users to talk with
        # if self._chosen_strategy == "infect":
        self._generate_communicators()
        #TODO where does the stay strategy happen?


        # for c in self.compromised: #TODO change the scope of the strategies to the attack object scope IMPOTANT!!!
        #     self._chosen_strategy = random.choice(self._strategies)
    #TODO implement the rest of the strategies' logic

    def advance(self):
        super().advance()

        # actually send packets
        for c in self.communicate_to:
            packet = self._generate_packet(destination=c)
            self._send(packet)
        self.communicate_to.clear()

        self._chosen_strategy = random.choice(self._strategies)

    def notify_victim_packet_generation(self, packet):
        # if self._chosen_strategy == "spread": # TODO strategies
        packet.add_payload(self._attack_of_choice)

    # def choose_strategy(self, org): #TODO calculations restricted to compromised for each organization
    #     comp_in_org = self.get_comp_in_org(org)
    #     #execute_utility = self.calculate_utility(comp_in_org/org.children, self._execute_risk)
    #     # execute_utility = random.random()
    #     #spread_utility = self.calculate_utility(1 - (comp_in_org/org.children), self._spread_risk)
    #     # spread_utility = random.random()
    #     #stay_utility = self.calculate_utility(0, self._stay_risk)
    #     # stay_utility = random.random()
    #
    #     #TODO fix this
    #     if (execute_utility > spread_utility) and (execute_utility > stay_utility):
    #         self.utility = execute_utility
    #         return "execute"
    #     elif (spread_utility > execute_utility) and (spread_utility > stay_utility):
    #         self.utility = execute_utility
    #         return "spread"
    #     else:
    #         self.utility = stay_utility
    #         return "stay"
        #TODO add some sort of randomness

    # def calculate_utility(self, payoff, risk):
    #     return payoff-risk

    def get_comp_in_org(self, org):
        comp_in_org = 0
        for c in self.compromised:
            if c.parent is org:
                comp_in_org += 1
        return comp_in_org




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
            detected = self.detect(c._attack_of_choice, targetted=False, passive=True)
            if detected:
                # self.parent.compromised_detected += 1
                self.clean_specific(c)
            else:
                self.parent.utility -= c.get_comp_in_org(self.parent) ** 2
                c.utility += c.get_comp_in_org(self.parent) ** 2 #TODO decide wether or not the attacker's utility is different for each org.

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
        # added self security and attack strategy risk to the equation due to the scope of the detection
        #TODO refine probabilities
        information = self.parent.attacks_list[attack]
        security = self._get_security()
        # defense = helpers.get_defense(security, information)
        # prob = helpers.get_prob_detection(defense, attack.effectiveness)
        # prob = helpers.get_prob_detection_v2(security, attack.effectiveness, information)

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

    def get_atk_strategy_risk(self, attack): #basic implementation
        atk_strategy = attack.original_source._chosen_strategy
        if atk_strategy == "infect":
            return 0.01
        elif atk_strategy == "stay":
            return 0.001
        elif atk_strategy == "spread":
            return 0.005
        return 0



