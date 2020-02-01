from agents.constructs import Correspondence
from agents.devices import NetworkDevice
from agents.constructs import *
import model
import random

class User(NetworkDevice):
    def __init__(self, activity, address, parent, model, routing_table, account_type, privilege, company_security, personal_security, media_presence, intention="None", work_done=0):
        self.intention = intention
        self.activity = activity
        self.parent = parent
        self.comm_table_in_size = random.randint(2, 10)
        self.comm_table_out_size = random.randint(0, 5)
        self.comm_table_size = self.comm_table_in_size + self.comm_table_out_size
        self.communications_devices = []
        self.communications_freq = []
        self.account_type = account_type #for determining the type of user account
        self.privilege = privilege #for determining the set of privileges said user has
        self.media_presence = media_presence
        self.user_security = self.weighted_user_security_level(s1=company_security,s2=personal_security,w1=0.3,w2=0.7)
        # for measuring the success of a user
        self.work_done = work_done
        super().__init__(address, parent, model, routing_table)

    def step(self):
        if len(self.communications_devices) == 0:  # communications table is uninitialized, lazy initialization
            self._generate_communications_table()

        r = random.random()
        if r < self.activity:
            dest = random.choices(self.communications_devices, weights=self.communications_freq, k=1)[0]
            Correspondence(self, dest, self.model)
            if model.VERBOSE:
                print("User %s establishing correspondence with %s" % (self.address, dest.address))

    def weighted_user_security_level(self,s1, s2, w1, w2):
        return (s1 * w1 + s2 * w2)/2

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

        s = sum(self.communications_freq)
        for i in range(len(self.communications_freq)):
            self.communications_freq[i] /= s

    # called by correspondence when correspondence is successful
    def add_to_work_done(self, importance):
        self.work_done = self.work_done + (importance / 10)
        if self.work_done > 1:
            self.work_done = 1

    def get_work_done(self):
        return self.work_done
