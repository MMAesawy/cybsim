from agents.devices import NetworkDevice
from helpers import *
import random

class User(NetworkDevice):
    def __init__(self, active, address, parent, model, routing_table):
        self.active = active
        self.comm_table_in_size = random.randint(2, 10)
        self.comm_table_out_size = random.randint(0, 5)
        self.comm_table_size = self.comm_table_in_size + self.comm_table_out_size
        self.communications_devices = []
        self.communications_freq = []
        self.parent = parent
        self.address = address
        super().__init__(address, parent, model, routing_table)



    def step(self):
        if(len(self.communications_devices) == 0):
            for i in range(self.comm_table_in_size):
                dest = random.choice(self.parent.children).address
                freq = random.random()
                self.communications_devices.append(dest)
                self.communications_freq.append(freq)

            for i in range(self.comm_table_out_size):
                dest = random.choice(self.model.devices).address
                if (not self.address.is_share_subnetwork(dest)):
                    freq = random.random()
                    self.communications_devices.append(dest)
                    self.communications_freq.append(freq)
                else: i -= 1

        r = random.random()
        if r < self.active: #TODO establish connection
            dest = self.communications_devices[random.randint(0,len(self.communications_devices) - 1)]
            packet = Packet(self.model.packet_count, dest, random.choice(self.model.packet_payloads))
            self.model.packet_count = self.model.packet_count + 1
            print("User %s attempting to message %s" % (self.address, dest))
            self.route(packet)
