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
        if not self.is_compromised(): # if not compromised any more
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

    def is_attack_successful(self, attack):
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

        self._strategies = ["stay", "spread", "infect", "execute"] #TODO execute strategy to get payoff
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
        if self._chosen_strategy == "infect":
            self._generate_communicators()

        for c in self.compromised: #TODO change the scope of the strategies to the attack object scope IMPOTANT!!!
            self._chosen_strategy = self.choose_strategy(c.parent)

    def advance(self):
        super().advance()

        # actually send packets
        for c in self.communicate_to:
            packet = self._generate_packet(destination=c)
            self._send(packet)
        self.communicate_to.clear()

    def notify_victim_packet_generation(self, packet):
        if self._chosen_strategy == "spread": # TODO strategies
            packet.add_payload(self._attack_of_choice)

    def choose_strategy(self, org): #TODO calculations restricted to compromised for each organization
        comp_in_org = self.get_comp_in_org(org)
        #execute_utility = self.calculate_utility(comp_in_org/org.children, self._execute_risk)
        execute_utility = random.random()
        #spread_utility = self.calculate_utility(1 - (comp_in_org/org.children), self._spread_risk)
        spread_utility = random.random()
        #stay_utility = self.calculate_utility(0, self._stay_risk)
        stay_utility = random.random()

        if (execute_utility > spread_utility) and (execute_utility > stay_utility):
            self.utility = execute_utility
            return "execute"
        elif (spread_utility > execute_utility) and (spread_utility > stay_utility):
            self.utility = execute_utility
            return "spread"
        else:
            self.utility = stay_utility
            return "stay"
        #TODO add some sort of randomness

    def calculate_utility(self, payoff, risk):
        return payoff-risk

    def get_comp_in_org(self, org):
        comp_in_org = 0
        for c in self.compromised:
            if c.parent is org:
                comp_in_org += 1
        return comp_in_org




class Employee(GenericDefender):

    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(activity, address, parent, model, routing_table)
        # TODO set restrictions on number of specific type.
        self.type = random.choice(["Front Office", "Back Office", "Security Team", "Developers"])

        self._security = None  # gets initialized as soon as _get_security is called.
        # do NOT use this variable directly

    def get_tooltip(self):
        return super().get_tooltip() + ("\nsecurity: %.2f" % self._get_security())

    def step(self):
        super().step()
        self._generate_communicators()
        for c in self.compromisers:
            detected = self.detect(c._attack_of_choice, True)
            if detected:
                self.parent.compromised_detected += 1
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

            self._security = ((security * 0.6) + (self.parent.company_security * 0.4)) / 2

        return self._security

    def is_attack_successful(self, attack): #detection function based chance
        if self.detect(attack):
            attack.utility -= 0.5
            return False
        else:
            attack.utility += 0.5
            return True

    def detect(self, attack, passive=False):
        # added self security and attack strategy risk to the equation due to the scope of the detection
        #TODO refine probabilities
        resistance = self.parent.attacks_list[attack]
        security_budget = self.parent.security_budget
        atk_strategy_risk = self.get_atk_strategy_risk(attack)
        prob = (atk_strategy_risk + self._get_security() + (1 - attack.effectiveness) + resistance + security_budget
                + self.parent.num_compromised / self.parent.num_users) / 6
        if passive:
            prob /= 4
        if random.random() < prob:  # attack is detected
            self.parent.attacks_list[attack] = (self.parent.attacks_list[attack] + 1.0) / 2
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



