from agents.agents import User
from agents.constructs import *
import model


class AttackClient(User):
    def __init__(self, activity, address, parent, model, routing_table, captured=None, intention="phishing"):
        super().__init__(activity, address, parent, model, routing_table)
        if captured is None: #list of devices that can be controlled
            captured = []
        self.intention = intention
        self.captured = captured
        self.control_cor_list = [] #actively controlled devices

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
                Correspondence(self, dest, self.model)
                if model.VERBOSE:
                    print("User %s establishing correspondence with %s" % (self.address, dest.address))
            else:
                if self.intention == "escalate":
                    # Initiating the escalate correspondence
                    self._escalate_if_captured()
                    self.comm_table_out_size = 0
                    self.comm_table_in_size = random.randint(5, 10)
                    self._generate_communications_table()  # Note: Should implement logic for initiating table locally.
                    # Unfinished code.

    def _generate_communications_table(self):
        # ensure the tables are empty
        self.communications_devices.clear()
        self.communications_freq.clear()

        # initialize devices inside the local network
        for i in range(self.comm_table_in_size):
            dest = random.choice(self.parent.children)
            freq = random.random()
            self.communications_devices.append(dest)
            self.communications_freq.append(freq)

        # initialize devices outside the local network
        for i in range(self.comm_table_out_size):
            dest = random.choice(self.model.devices)
            if not self.address.is_share_subnetwork(
                    dest.address):  # only add if the device is outside the local network
                freq = random.random()
                self.communications_devices.append(dest)
                self.communications_freq.append(freq)
            else:
                i -= 1

    #  A function for Initiating correspondence with the captured devices.
    def _escalate_if_captured(self):
        for i in range(len(self.captured)):
            if len(self.control_cor_list) != 0:
                for j in range(len(self.control_cor_list)):
                    if self.captured[i].address.__eq__(self.control_cor_list[j].address):
                        continue
                    else:
                        Correspondence(self, self.captured[i], self.model, None, None, [1])
                        if model.VERBOSE:
                            print("User %s establishing correspondence with %s" % (self.address, self.captured[i].address))
                        self.control_cor_list.append(self.captured[i])
            else:
                Correspondence(self, self.captured[i], self.model, None, None, [1])
                if model.VERBOSE:
                    print("User %s establishing correspondence with %s" % (self.address, self.captured[i].address))
                self.control_cor_list.append(self.captured[i])

