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


    def step(self):
        if len(self.communications_devices) == 0:  # communications table is uninitialized, lazy initialization
            self.comm_table_out_size = random.randint(3, 6)
            self.comm_table_in_size = 0
            self._generate_communications_table()
        for c in self.communications_devices:
            print("comm..", c.address)


        for  d in self.controlled_orgs:
            print("orgs..", d[0], d[1])
        r = random.random()
        if r < 1: #testing attack every time
            # communication devices only contain devices form non compromised orgs
            # try to attack other non compromised organizations
            # attacker cannot continue infilterating compromised orgs
            # TODO add coniditon that checks how many other subnetworks are blocked
            if len(self.controlled_orgs) != self.model.num_subnetworks:
                dest = random.choices(self.communications_devices, weights=self.communications_freq, k=1)[0]
                # Initiating the phishing correspondence.
                print("victim..", dest.address)
                AttackCorrespondence(self, dest, self.model)
                if model.VERBOSE:
                    print("Attacker %s establishing correspondence with %s" % (self.address, dest.address))
            else:
                print("Attacker %s has infilterated all organization..."% (self.address))

            # choose strategy for each compromised organization

            for i, org in enumerate(self.controlled_orgs):
                strategy = random.choice(['stay', 'spread', 'execute'])
                org[1] = strategy

                print("chosen strat..", org[0], org[1])
                if strategy == 'execute':
                    self.execute(org)
                if strategy == 'stay':
                    #TODO increase % detection
                    pass
                if strategy == 'spread':
                    self.spread(org)

            self.update_utility()

    def execute(self,org):
        if model.VERBOSE:
            print("Attacker has executed attack on organization %s with utility %f" % (org, self.utility))
        for device in self.captured:  # remove all captured devices from list once executed
            if (device.address.get_subnet() == org[0]):
                device.clean()
                self.captured.remove(device)
                self.model.total_compromised -= 1

        self.controlled_orgs.remove(org)  # remove organization from control
        # TODO gateway device block controlled_by address

    def spread(self, org):

        for device in self.captured:
            print("aaaaaaaa",device.address, device.state)
            if (device.address.get_subnet() == org[0]):
                print("spreading in network", org[0], "with num comp", device.get_num_compromised(), "out of ", device.parent.num_users)
                # make sure that spreading only occurs if compromised network still has Safe devices
                if(device.get_num_compromised() != device.parent.num_users):
                    if model.VERBOSE:
                        print("Attacker spreading attack in organization %s through device %s" % (org[0], device.address))
                    print("deviceee spread pre", device.address, self, device.state)
                    device.spread()
                else:
                    print("All devices on organization %s are compromised.." %(org[0]))
                    return

    def update_utility(self):
        self.utility = len(self.captured) / self.model.num_users

    def receive(self, victim):
        # print("victim..", victim.address)
        # victim.infect(self)
        # self.captured.append(victim)
        # # add victim from new organization to controlled orgs
        # # print("org..", self.controlled_orgs)
        # if len(self.controlled_orgs) != 0:
        #     if (victim.address.get_subnet() not in org[0] for org in self.controlled_orgs):
        #         self.controlled_orgs.append([victim.address.get_subnet(), None])
        # else:
        #     self.controlled_orgs.append([victim.address.get_subnet(), None])
        #
        #
        # self.model.total_compromised += 1
        # # once an organization is infiltrated, remove all other entry points
        #
        # self.cease_communications(victim)
        # print("victim..", victim.address)
        victim.infect(self)
        self.captured.append(victim)
        print("appended victim..", victim.address, victim.state)


        org_list = self.create_list(victim.address.get_subnet(), self.controlled_orgs)
        if len(self.controlled_orgs) != 0:
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
        i = 0
        while i < self.comm_table_out_size:
            dest = random.choices(self.model.users, weights=[x.media_presence for x in self.model.users], k=1)[0]
            # only add if the device is outside the local network
            if dest.state == "Safe":
                if not self.address.is_share_subnetwork(dest.address):
                    if (len(self.controlled_orgs) != 0):
                        # and is not in an already compromised organization
                        if (dest.address.get_subnet() not in org[0] for org in self.controlled_orgs):
                        # if (dest.address.get_subnet() not in self.controlled_orgs[0]):
                            freq = random.random()
                            self.communications_devices.append(dest)
                            self.communications_freq.append(freq)
                            i += 1
                        else:
                            i -= 1
                    else:
                        freq = random.random()
                        self.communications_devices.append(dest)
                        self.communications_freq.append(freq)
                        i += 1
                else:
                    i -= 1
            else:
                i -= 1


