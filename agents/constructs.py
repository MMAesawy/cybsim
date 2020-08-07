import re
from helpers import random_string
import random
import globalVariables
import numpy as np

if globalVariables.GLOBAL_SEED:
    np.random.seed(globalVariables.GLOBAL_SEED_VALUE)
    random.seed(globalVariables.GLOBAL_SEED_VALUE)

class Attack:
    def __init__(self, original_source, attack_type=None):
        self.original_source = original_source
        # self.effectiveness = random.random() / 2 + 0.5  # TODO effectiveness or skill of attacker? weighted sum?
        if self.original_source.model.fixed_attack_effectiveness:
            self.effectiveness = self.original_source.model.fixed_attack_effectiveness_value
            max(0, min(1, random.gauss(0.5, 1 / 6)))  # dummy, for consistent randomness during branching
        else:
            self.effectiveness = max(0, min(1, random.gauss(0.5, 1/6)))
        if attack_type:
            self.attack_type = attack_type
            random_string(length=8)  # dummy, for consistent randomness during branching
        else:
            self.attack_type = random_string(length=8)

    def __eq__(self, other):
        return self.attack_type == other.attack_type

    def __hash__(self):
        return hash(self.attack_type)

    def carry_out_attack(self, source, destination):
        """
        Executes the attack. Will not execute if the original_source is not set.
        :param source: the sender of the packet (the attacker)
        :param destination: the destination of the packet (the victim)
        :return: whether or not the attack is successful
        """
        if not self.original_source:
            return False
        defender = destination
        targeted = source == self.original_source
        if defender.is_attack_successful(attack=self, targeted=targeted):
            if defender not in self.original_source.compromised:  # defender is not compromised by this attacker
                self.original_source.infect(defender)
                return True
            else:
                return False
        elif not targeted:
            source.clean_specific(self.original_source)
        return False

    def __str__(self):
        return "Attack of type: %s" % self.attack_type


class Packet:
    total_packet_count = 0

    def __init__(self, model, source, destination, payload=None, step=0):
        self.packet_id = Packet.total_packet_count
        Packet.total_packet_count += 1
        self.source = source
        self.destination = destination
        self.payload = payload
        self.step = step
        self.model = model
        self.max_hops = -1  # -1 == no maximum hops

    def add_payload(self, payload):
        if type(self.payload) is list and len(self.payload) > 0:
            self.payload.append(payload)
        elif self.payload is not None:
            self.payload = [self.payload, payload]
        else: # No existing payload
            self.payload = payload

    def execute_payload(self):
        """
        Executes the payload.
        :return: the return of the payload execute function, if exists.
        """

        if type(self.payload) is list:
            for p in self.payload:
                p.carry_out_attack(self.source, self.destination)
        elif self.payload is not None:
            self.payload.carry_out_attack(self.source, self.destination)


class AddressServer:
    """
        Controls and facilitates the conversion between a hierarchical address (e.g. 1.22.1.3)
        and a numerical serial address. Needed for Mesa's visualization engine
    """

    def __init__(self, initial=0):
        self.next_address = initial
        self.addresses = {}

    def __contains__(self, item):
        return item in self.addresses

    def __getitem__(self, address):
        if address not in self.addresses:
            self.addresses[address] = self.next_address
            self.next_address += 1
            return self.next_address - 1
        else:
            return self.addresses[address]

    def reverse_lookup(self, address):
        for k, v in self.addresses.items():
            if v == address:
                return k
        return None


class Address:
    _r = re.compile(r"(\d+)\s*([,.]|$)")
    def __init__(self, address):
        self.address = []

        # if the address is a string, parse the address into its components
        if isinstance(address, str):
            for m in Address._r.finditer(address):
                if m:
                    self.address.append(m.group(1))
        elif isinstance(address, int):
            self.address = [address]
        elif isinstance(address, list) or isinstance(address, tuple):
            # iterate to avoid tuple immutability, also as a way to copy
            for a in address:
                self.address.append(a)

    def is_share_subnetwork(self, other):
        i = 0
        while i < min(len(self), len(other)) and self[i] == other[i]:
            i += 1
        return i >= len(self) - 1

    def is_supernetwork(self, other):
        if len(self) > len(other):
            return False
        i = 0
        while i < min(len(self), len(other)) and self[i] == other[i]:
            i += 1
        return i == len(self)

    def get_subnet(self):
        if len(self.address) > 1:
            return Address(self.address[:-1])
        else:
            return None

    def __str__(self):
        return ".".join([str(a) for a in self.address])

    def __getitem__(self, item):
        return self.address[item]

    def __int__(self):
        return int("".join([str(a) for a in self.address]))

    def __len__(self):
        return len(self.address)

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        if self.n > len(self):
            raise StopIteration
        else:
            result = self[self.n]
            self.n += 1
            return result

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        for i in range(len(self)):
            if self[i] != other[i]:
                return False
        return True

    def __add__(self, other):
        if other is Address:
            return Address(self.address + other.address)
        elif isinstance(other, list) or isinstance(other, tuple):
            return Address(self.address + other)
        elif isinstance(other, int):
            return Address(self.address + [other])
        else:
            raise ValueError("Address addition error: 'other' is of invalid type: %s" % str(type(other)))

    def __setitem__(self, key, value):
        self.address[key] = value

    def __hash__(self):
        return hash(str(self))
