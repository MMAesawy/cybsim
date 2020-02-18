from agents.agents import User
from agents.constructs import *
from agents.agents import Employee
import model


class AttackClient(User):
    def __init__(self, activity, address, parent, model, routing_table, utility = 0, captured=None, intention="phishing", state="Inactive"):
        super().__init__(activity, address, parent, model, routing_table)
        if captured is None: #list of devices that can be controlled
            captured = []
        self.intention = intention
        self.captured = captured
        self.state = state
        self.model = model
        self.utility = utility
        self.controlled_orgs = []


    def step(self):
        if len(self.communications_devices) == 0:  # communications table is uninitialized, lazy initialization
            self.comm_table_out_size = random.randint(3, 6)
            self.comm_table_in_size = 0
            self._generate_communications_table()


        r = random.random()
        if r < self.activity:
            # communication devices only contain devices form non compromised orgs
            dest = random.choices(self.communications_devices, weights=self.communications_freq, k=1)[0]
            # Initiating the phishing correspondence.
            AttackCorrespondence(self, dest, self.model)
            if model.VERBOSE:
                print("Attacker %s establishing correspondence with %s" % (self.address, dest.address))

            #try to attack other non compromised organizations
            for i, org in enumerate(self.controlled_orgs):
                strategy = random.choice(['execute', 'stay', 'spread'])
                self.controlled_orgs[i][1] = strategy
                if(strategy == 'execute'):
                    if model.VERBOSE:
                        print("Attacker has executed attack on organization %s with utility %f" % (org[i][0], self.utility))
                    for device in self.captured: # remove all captured devices from list once executed
                        if (device.address.get_subnet() == self.controlled_orgs[i][0]):
                            self.captured.remove(device)
                    self.controlled_orgs.pop(i)  # remove organization from control
                        #TODO gateway device block controlled_by address
                        #TODO change all compromised devices to be free
                if(strategy == 'stay'):
                    #increase % detection
                    pass

            self.update_utility()

    def update_utility(self):
        self.utility = len(self.captured) / self.model.num_users

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
            # only add if the device is outside the local network
            if not self.address.is_share_subnetwork(dest.address):
                if (len(self.controlled_orgs) != 0):
                    # and is not in an already compromised organization
                    if (dest.address.get_subnet() not in org[0] for org in self.controlled_orgs):
                        freq = random.random()
                        self.communications_devices.append(dest)
                        self.communications_freq.append(freq)
                    else:
                        i -= 1
                else:
                    freq = random.random()
                    self.communications_devices.append(dest)
                    self.communications_freq.append(freq)
            else:
                i -= 1

