from agents.agents import User
from agents.constructs import *
from agents.agents import Employee
import model


class AttackClient(User):
    def __init__(self, activity, address, parent, model, routing_table, captured=None, intention="phishing", state="Inactive"):
        super().__init__(activity, address, parent, model, routing_table)
        if captured is None: #list of devices that can be controlled
            captured = []
        self.intention = intention
        self.captured = captured
        self.state = state
        self.model = model

    def step(self):
        if len(self.communications_devices) == 0:  # communications table is uninitialized, lazy initialization
            self.comm_table_out_size = random.randint(3, 6)
            self.comm_table_in_size = 0
            self._generate_communications_table()

        r = random.random()
        if r < self.activity:
            if len(self.captured) == 0: #TODO target specific users for phishing
                dest = random.choices(self.communications_devices, weights=self.communications_freq, k=1)[0]
                # Initiating the phishing correspondence.
                AttackCorrespondence(self, dest, self.model)
                if model.VERBOSE:
                    print("Attacker %s establishing correspondence with %s" % (self.address, dest.address))

    def _generate_communications_table(self):
        # ensure the tables are empty
        self.communications_devices.clear()
        self.communications_freq.clear()

        # initialize devices inside the local network
        for i in range(self.comm_table_in_size):
            dest = random.choices(self.parent.users_on_subnetwork, weights=[x.media_presence for x in self.parent.users_on_subnetwork], k=1)[0]
            freq = random.random()
            self.communications_devices.append(dest)
            self.communications_freq.append(freq)

        # initialize devices outside the local network
        for i in range(self.comm_table_out_size):
            dest = random.choices(self.model.users, weights=[x.media_presence for x in self.model.users], k=1)[0]
            if not self.address.is_share_subnetwork(dest.address):  # only add if the device is outside the local network
                freq = random.random()
                self.communications_devices.append(dest)
                self.communications_freq.append(freq)
            else:
                i -= 1

