from agents.agents import User
from agents.constructs import AttackCorrespondence
import random
import model


class AttackClient(User):
    def __init__(self, activity, address, parent, model, routing_table, utility = 0, captured=None, intention="phishing"):
        super().__init__(activity, address, parent, model, routing_table)
        if captured is None: #list of devices that can be controlled
            captured = []
        self.intention = intention
        self.captured = captured
        self.model = model
        self.utility = utility
        self.controlled_orgs = []
        self.skill = random.random() #TODO think about probabilities and how they interact with each other IMPORTNANTTNTSJNTJsn


    def step(self):
        r = random.random()
        if r < self.activity:
            # communications table is uninitialized, lazy initialization
            if len(self.communications_devices) == 0:
                # communication devices only contain devices form non compromised orgs
                if len(self.controlled_orgs) != self.model.num_subnetworks - 1:
                    # attacker cannot communicate with compromised devices
                    if self.model.num_users != self.model.total_compromised:
                        # maximum_range =
                        maximum = int((self.model.num_users - self.model.total_compromised) / 10)
                        minimum = min(self.model.num_subnetworks - 1 - len(self.controlled_orgs), maximum)
                        self.comm_table_out_size = random.randint(minimum, maximum)
                        self.comm_table_in_size = 0
                        if(self.comm_table_out_size == 0):
                            self.comm_table_out_size = 1
                            self._generate_communications_table()
                            self.communicate()
                    else:
                        if model.VERBOSE:
                            print("All devices are compromised...")
                else:
                    if model.VERBOSE:
                        print("Attacker %s has infiltrated all organization..."% (self.address))
            else:
                self.communicate()


            self.strategize()
            self.update_utility()


            # choose strategy for each compromised organization

    def calculate_ranges(self):
        pass


    def communicate(self):
        dest = random.choices(self.communications_devices, weights=self.communications_freq, k=1)[0]
        # Initiating the phishing correspondence.
        AttackCorrespondence(self, dest, self.model)
        if model.VERBOSE:
            print("Attacker %s establishing correspondence with %s" % (self.address, dest.address))

    def strategize(self):
        for i, org in enumerate(self.controlled_orgs):
            strategy = random.choice(['stay', 'spread', 'execute'])
            org[1] = strategy
            for j in range(len(self.model.subnetworks)):  # This loop is for retrieving organization objects.
                if org[0] == self.model.subnetworks[j].address:
                    cur_org = self.model.subnetworks[j]
                if strategy == 'execute':
                    self.execute(org)
                if strategy == 'stay':
                    if random.random() < cur_org.children[0].get_probability_detection(self.skill, self.address):
                        self.got_detected(org)
                    else:
                        pass
                if strategy == 'spread':
                    if random.random() < cur_org.children[0].get_probability_detection(self.skill, self.address):
                        self.got_detected(org)
                    else:
                        self.spread(org)

    def got_detected(self, org):
        added = False
        for device in self.captured:  # remove all captured devices from list once executed
            if (device.address.get_subnet() == org[0]):
                device.clean()
                self.captured.remove(device)
                self.model.total_compromised -= 1
                if not added:
                    device.parent.blocking_list.append(self.address)

        self.controlled_orgs.remove(org)  # remove

    def execute(self,org):
        # TODO Increase or decrease utility when executing.

        if model.VERBOSE:
            print("Attacker has executed attack on organization %s with utility %f" % (org, self.utility))
        self.got_detected(org)


    def spread(self, org):
        for device in self.captured:
            if (device.address.get_subnet() == org[0]):
                # make sure that spreading only occurs if compromised network still has Safe devices
                if(device.get_num_compromised() != device.parent.num_users):
                    if model.VERBOSE:
                        print("Attacker spreading attack in organization %s through device %s" % (org[0], device.address))
                    device.spread()
                else:
                    if model.VERBOSE:
                        print("All devices on organization %s are compromised.." %(org[0]))
                    return

    def update_utility(self):
        self.utility = len(self.captured) / self.model.num_users

    def receive(self, victim):
        victim.infect(self)
        self.captured.append(victim)
        if len(self.controlled_orgs) != 0:
            org_list = self.create_list(victim.address.get_subnet(), self.controlled_orgs)
            if not any(org_list): # make sure only new unique orgs are added
                self.controlled_orgs.append([victim.address.get_subnet(), None])
        else:
            self.controlled_orgs.append([victim.address.get_subnet(), None])

        self.model.total_compromised += 1

        # once an organization is infiltrated, remove all other entry points

        self.cease_communications(victim)



    def create_list(self,victim_address, control_org_list):
        org_list = []
        for org in control_org_list:
            if (victim_address == org[0]):
                org_list.append(True)
            else:
                org_list.append(False)
        return org_list


    def cease_communications(self, compromised_device):
        for i, device in enumerate(self.communications_devices):
            if (device.address.is_share_subnetwork(compromised_device.address)):
                self.communications_devices.pop(i)
                self.communications_freq.pop(i)

    def _generate_communications_table(self):
        # ensure the tables are empty
        self.communications_devices.clear()
        self.communications_freq.clear()

        # initialize devices inside the local network
        # self.comm_table_in_size = 0, no attacking own network
        for i in range(self.comm_table_in_size):
            dest = random.choices(self.parent.users_on_subnetwork, weights=[x.media_presence for x in self.parent.users_on_subnetwork], k=1)[0]
            freq = random.random()
            self.communications_devices.append(dest)
            self.communications_freq.append(freq)

        # initialize devices outside the local network
        while (len(self.communications_devices) < self.comm_table_out_size):
            dest = random.choices(self.model.users, weights=[x.media_presence for x in self.model.users], k=1)[0]
            # only add if the device is outside the local network
            if dest.state == "Safe":
                if not self.address.is_share_subnetwork(dest.address):
                    if (len(self.controlled_orgs) != 0):
                        # and is not in an already compromised organization
                        org_list = self.create_list(dest.address.get_subnet(), self.controlled_orgs)
                        if not any(org_list):
                            freq = random.random()
                            self.communications_devices.append(dest)
                            self.communications_freq.append(freq)

                    else: # no organizations in control
                        freq = random.random()
                        self.communications_devices.append(dest)
                        self.communications_freq.append(freq)
