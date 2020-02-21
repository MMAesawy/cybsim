from agents.devices import NetworkDevice
from agents.constructs import *
# from agents.constructs import Correspondence
import random
import model



class User(NetworkDevice):
    def __init__(self, activity, address, parent, model, routing_table):
        super().__init__(address, parent, model, routing_table)
        self.activity = activity
        self.parent = parent
        self.comm_table_in_size = random.randint(1, self.parent.num_users)
        self.comm_table_out_size = random.randint(0, 5)
        self.comm_table_size = self.comm_table_in_size + self.comm_table_out_size
        self.communications_devices = []
        self.communications_freq = []



class Employee(User):
    def __init__(self, activity, address, parent, model, routing_table,
                 account_type, company_security, personal_security,
                 media_presence, intention=None, state="Safe", controlled_by=None, work_done=0):
        super().__init__(activity, address, parent, model, routing_table)
        # self.intention = intention

        self.account_type = account_type  # for determining the type of user account
        self.media_presence = media_presence
        self.intention = intention
        self.state = state
        self.controlled_by = controlled_by
        self.security = self.weighted_user_security_level(s1=company_security, s2=personal_security, w1=0.3, w2=0.7)
        self.immune_from = []
        self.malicious_communications_devices = []
        self.malicious_communications_freq = []
        self.comm_table_in_size = random.randint(1, self.parent.num_users - self.parent.num_compromised)
        print("user com size in", self.comm_table_in_size)


        # for measuring the success of a user
        self.work_done = work_done

        model.users.append(self) #append user into model's user list

    def weighted_user_security_level(self, s1, s2, w1, w2):
        return (s1 * w1 + s2 * w2) / 2

    def step(self):
       self.communicate()

    def infect(self, attacker):
        self.state = "Compromised"
        self.controlled_by = attacker
        self.parent.num_compromised += 1


    def clean(self):
        self.state = "Safe"
        self.controlled_by = None
        self.parent.num_compromised -= 1
        self.malicious_communications_devices.clear()
        self.malicious_communications_freq.clear()

    def communicate(self): # normal communications with either safe or none safe device
        if len(self.communications_devices) == 0:  # communications table is uninitialized, lazy initialization
            self._generate_communications_table()

        r = random.random()
        if r < self.activity:
            dest = random.choices(self.communications_devices, weights=self.communications_freq, k=1)[0]
            Correspondence(self, dest, self.model)
            if model.VERBOSE:
                print("User %s establishing correspondence with %s" % (self.address, dest.address))

    def _generate_malicious_communications_table(self):
        # ensure the tables are empty
        self.malicious_communications_devices.clear()
        self.malicious_communications_freq.clear()

        # initialize devices inside the local network
        counter = 0
        print(self.comm_table_in_size)
        while len(self.malicious_communications_devices) < self.comm_table_in_size:
            dest = random.choices(self.parent.users_on_subnetwork,
                                  weights=[x.media_presence for x in self.parent.users_on_subnetwork], k=1)[0]
            print("malicious commm...", dest.address, dest.state)

            if (dest.state == 'Safe'): # only attack non compromised devices
                freq = random.random()
                self.malicious_communications_devices.append(dest)
                self.malicious_communications_freq.append(freq)
            else:
                counter += 1

    def get_num_compromised(self):
        return self.parent.num_compromised

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
        while len(self.communications_devices) < self.comm_table_out_size:
            dest = random.choice(self.model.devices)
            if not self.address.is_share_subnetwork(dest.address):  # only add if the device is outside the local network
                freq = random.random()
                self.communications_devices.append(dest)
                self.communications_freq.append(freq)


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

    def spread(self):  # For spreading the attack through the organization.
        print("sss",len(self.malicious_communications_devices))
        print(self.get_num_compromised())
        print(self.parent.num_users)
        if len(self.malicious_communications_devices) == 0:  # communications table is uninitialized, lazy initialization
            print("generating!!")
            self._generate_malicious_communications_table()

        r = random.random()
        if r < 1: # for testing
            print("sss2",len(self.malicious_communications_devices))
            dest = random.choices(self.malicious_communications_devices, weights=self.malicious_communications_freq, k=1)[0]
            print("spreading from device" ,self.address)
            print("attacker", self.controlled_by.address," to " ,dest.address)
            AttackCorrespondence(self.controlled_by, dest, self.model)
            if model.VERBOSE:
                print("Compromised User %s establishing correspondence with %s" % (self.address, dest.address))

    def receive(self, victim):
        self.controlled_by.receive(victim)

    def get_probability_detection(self, effectiveness, attackerAddress):
        if attackerAddress in self.parent.blocking_list:
            isKnown = 1
        else:
            isKnown = 0
        securityBudget = self.parent.security_budget
        return (1 - effectiveness + isKnown + securityBudget) / 3
