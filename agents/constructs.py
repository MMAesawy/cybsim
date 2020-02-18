from __future__ import annotations
import re
import random


class Correspondence:
    def __init__(self, party_a, party_b, model, fails_to_end=None, sequence_length=None, sequence=None):
        self.party_a = party_a
        self.party_b = party_b
        self.fails_to_end = fails_to_end
        self.model = model

        if sequence is None:
            self.sequence = self._generate_sequence(sequence_length)

        else:
            self.sequence = sequence

        self.failure_count = 0
        self.pointer = 0
        # self.total_failure_count = 0
        self.ready_state = True
        self.active = True

        self.model.active_correspondences.append(self)

        self.importance_level = random.randint(0, 10)

    def _generate_sequence(self, sequence_length=None):
        if sequence_length is None:
            if self.party_a.intention == "phishing":  # <-- rudimentary code for initializing the sequence of an attack
                sequence_length = random.randint(1, 4)
                sequence = random.choices([1], weights=None, k=sequence_length)
                return sequence
            else:
                sequence_length = random.randint(5, 15)
                return random.choices((0, 1, 2), weights=None, k=sequence_length)

    def __len__(self):
        return len(self.sequence)

    def step(self):
        if self.ready_state and self.active:
            self.ready_state = False
            next_action = self.sequence[self.pointer]
            if next_action == 0:
                self.packet_success()
                return

            if self.party_a.intention == "phishing":  # If the correspondence is initiated by an attacker
                if next_action == 1:
                    packet = PhishingPacket(self.model, self.party_b.address, self)  # Note: i think packets should be initialized from a Client or User object, unrealistic to be initialized from correspondence. (for setting effectiveness for example)

                    security_awareness = self.party_b.security
                    if packet.effectiveness > security_awareness:  # If lower than chance of responding, a 2 is inserted into the sequence after the current position to signify a user responding.
                        self.sequence.insert(random.randint(self.pointer + 1, len(self.sequence)), 2)
                    self.party_a.route(packet)

                elif next_action == 2:
                    packet = InfoPacket(self.model, self.party_a.address, self)  # Note: Should compute the vital or not parameter later. (for now it's always True for testing)
                    self.party_b.route(packet)

            elif self.party_a.intention == "escalate":  # If the correspondence is initiated by an attacker to escalate privilege.
                if next_action == 1:
                    packet = ControlPacket(self.model, self.party_b.address, self)
                    self.sequence.append(random.choice((1, 2)))
                    self.party_a.route(packet)

                elif next_action == 2:
                    packet = InfoPacket(self.model, self.party_a.address, self)  # Note: Should compute the vital or not parameter later. (for now it's always True for testing)
                    self.sequence.append(random.choice((1, 2)))
                    self.party_b.route(packet)

            else:
                if next_action == 1:
                    packet = Packet(self.model, self.party_b.address, self)
                    self.party_a.route(packet)
                elif next_action == 2:
                    packet = Packet(self.model, self.party_a.address, self)
                    self.party_b.route(packet)

    def packet_success(self):
        self.pointer += 1
        self.failure_count = 0
        self.ready_state = True

        if self.pointer >= len(self):
            self.end_correspondence(True)

    def packet_failed(self):
        self.failure_count += 1
        self.model.total_failure_count += 1
        self.ready_state = True

        if self.fails_to_end and self.failure_count >= self.fails_to_end:
            self.end_correspondence(False)

    def end_correspondence(self, success):
        self.ready_state = False
        self.active = False

        if success:  # if correspondence ended successfully
            if self.party_a.intention == "phishing":
                self.party_a.intention = "escalate"  # Changing the attacker's intention here.
            if len(set(self.sequence)) == 1 and self.sequence[0] == 0:
                pass
            elif len(set(self.sequence)) == 1 and self.sequence[0] == 1:
                self.party_a.add_to_work_done(self.importance_level)
            elif len(set(self.sequence)) == 1 and self.sequence[0] == 2:
                if type(self.party_b) == type(self.party_a):
                    self.party_b.add_to_work_done(self.importance_level)
            else:
                self.party_a.add_to_work_done(self.importance_level)
                if type(self.party_b) == type(self.party_a):
                    self.party_b.add_to_work_done(self.importance_level)
        else:
            pass


class Packet:
    total_packet_count = 0
    packet_payloads = ["Just passing through!", "IDK anymore...", "Going with the flow!", "Leading the way.",
                       "Taking the high road!", "I'm on the hiiiiiighway to hell!", "gg ez",
                       "I want to go home ):", "It's funny how, in this journey of life, even though we may "
                                               "begin at different times and places, our paths cross with "
                                               "others so that we may share our love, compassion, observations"
                                               ", and hope. This is a design of God that I appreciate and "
                                               "cherish.",
                       "It's all ogre now.", "I need to go", "Seeing is believing!", "I've been on these roads"
                                                                                     " for as long as i can "
                                                                                     "remember..."]

    def __init__(self, model, destination, correspondence, payload=None, step=0):
        self.packet_id = Packet.total_packet_count
        Packet.total_packet_count += 1
        self.destination = destination
        self.payload = payload if payload else random.choice(Packet.packet_payloads)
        self.correspondence = correspondence
        self.step = step
        self.model = model
        self.max_hops = -1 # -1 == no maximum hops

    def drop(self):
        self.correspondence.packet_failed()

    def received(self):
        self.correspondence.packet_success()


# A child class for the packet that the attacker would send to the victim hoping that they would retrieve info.
class PhishingPacket(Packet):
    packet_payloads = ["You've just won an iphone 11 pro extreme xl !!!!", "This is the real google and someone is "
                                                                           "trying to hack you! Reset your password "
                                                                           "by typing yor old one in NAW!!!",
                       "This is IT, i totally forgot what was your machine's password, can you remind me please?"]

    def __init__(self, model, destination, correspondence, effectiveness=1, payload=None, step=0):
        super().__init__(model, destination, correspondence, payload=None, step=0)
        self.effectiveness = effectiveness #TODO function to determine effectiveness of attack
        self.payload = payload if payload else random.choice(PhishingPacket.packet_payloads)
        self.step = step

    def drop(self):
        self.correspondence.packet_failed()

    def received(self):
        self.correspondence.packet_success()


#  A child class for the packet that the victim would send back if phishing is successful for example.
class InfoPacket(Packet):
    packet_payloads = ["Here is my info (;", "YEYEYEYEYEYEYEY", "Oh wow! okay okay, here is my password :)"]

    # The vital flag is to signify that this information will allow the attacker to escalate privilege once. (set to True for testing)
    def __init__(self, model, destination, correspondence, vital=True, payload=None,step=0):
        super().__init__(model, destination, correspondence, payload=None, step=0)
        self.vital = vital
        self.payload = payload if payload else random.choice(InfoPacket.packet_payloads)
        self.step = step

    def drop(self):
        self.correspondence.packet_failed()

    def received(self):
        self.correspondence.packet_success()
        if self.vital is True:
            for i in range(len(self.correspondence.party_a.captured)):
                if self.correspondence.party_b.address.__eq__(self.correspondence.party_a.captured[i].address):
                    return
            self.correspondence.party_a.captured.append((self.correspondence.party_b, ""))
            self.correspondence.party_b.state = "Compromised"
            self.correspondence.party_b.controlled_by = self.correspondence.party_a
            self.model.total_compromised += 1
            for d in self.correspondence.party_a.captured: #once an organization is infilterated, remove all other entry points
                if(d.address.is_share_subnetwork(self.correspondence.party_b)):
                    self.correspondence.party_a.remove(self.correspondence.party_b)



#  A child class for the packets that are sent from an attacker to control a captured device
class ControlPacket(Packet):
    packet_payloads = ["MOOORE! BRING ME MOOOOOORE!!!", "Do this and do that.", "GO MY MINION!"]

    def __init__(self, model, destination, correspondence, payload=None, step=0):
        super().__init__(model, destination, correspondence, payload=None, step=0)
        self.payload = payload if payload else random.choice(ControlPacket.packet_payloads)
        self.step = step

    def drop(self):
        self.correspondence.packet_failed()

    def received(self):
        self.correspondence.packet_success()


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
    def __init__(self, address):
        self.address = []

        # if the address is a string, parse the address into its components
        if isinstance(address, str):
            r = re.compile(r"(\d+)\s*([,.]|$)")
            for m in r.finditer(address):
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
