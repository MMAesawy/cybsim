import re
import random


class Correspondence:
    def __init__(self, party_a, party_b, model, fails_to_end=None, sequence_length=None):
        self.party_a = party_a
        self.party_b = party_b
        self.fails_to_end = fails_to_end
        self.model = model

        self.sequence = self._generate_sequence(sequence_length)
        self.failure_count = 0
        self.pointer = 0
        # self.total_failure_count = 0
        self.ready_state = True
        self.active = True

        self.model.active_correspondences.append(self)

        self.importance_level = random.randint(0, 10)

    def _generate_sequence(self, sequence_length=None):
        if sequence_length is None:
            sequence_length = random.randint(5, 15)
        return random.choices((0, 1, 2), weights=None, k=sequence_length)

    def __len__(self):
        return len(self.sequence)

    def step(self):
        if self.ready_state and self.active:
            next_action = self.sequence[self.pointer]
            if next_action == 0:
                self.packet_success()
                return
            if next_action == 1:
                packet = Packet(self.model, self.party_b.address, self)
                self.party_a.route(packet)
            elif next_action == 2:
                packet = Packet(self.model, self.party_a.address, self)
                self.party_b.route(packet)
        self.ready_state = False

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
        self.max_hops = self.model.max_hops
        self.max_hops = self.model.max_hops

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
