from mesa.agent import Agent
import model


class NetworkDevice(Agent):

    def __init__(self, address, parent, model, routing_table):
        super().__init__(address, model)

        self.address = address
        self.parent = parent
        self.model = model
        self.routing_table = routing_table
        self.packets_received = 0
        self.packets_sent = 0
        self.current_packets = []
        # self.type = self.parent.type
        self.passing_packets = 0
        self.capacity = -1  # -1 == infinite capacity

        # a list to store packet payloads in the device
        self.occupying_packets = []

        # retrieve master address
        self.master_address = model.address_server[self.address]

        # append to the main model's device list. For convenience.
        model.devices.append(self)

        # append itself to the master graph
        if self.master_address not in model.G.nodes:
            model.G.add_node(self.master_address)

    def get_tooltip(self):
        return "address: %s\n" \
               "packets sent: %d\n" \
               "packets received: %d" \
                % (self.address,
                 self.packets_sent,
                 self.packets_received)

    def route(self, packet):
        if self.capacity < 0 or self.passing_packets < self.capacity:
            self.passing_packets += 1
            if self.address == packet.destination.address:  # this device is the recipient
                self._receive(packet)
            else:
                self._send(packet)
        else:
            if model.VERBOSE:
                print("Device %s reached its capacity of %d, dropping packet %d..." %
                      (self.address, self.capacity, packet.packet_id))
            packet.drop()

    def gateway_device(self):
        """Returns itself. This is the base condition of the SubNetwork.gateway_device() function."""
        return self

    def _receive(self, packet):
        """
        Logic for receiving a network packet.
        :param packet: the packet to be received
        """
        self.packets_received += 1
        self.occupying_packets.append(packet)
        self.model.total_packets_received += 1
        if model.VERBOSE:
            print("Device %s received packet: %s" % (self.address, packet.payload))

    def _send(self, packet):
        """
        Logic for sending a network packet.
        :param packet: packet to send
        """
        if packet.max_hops < 0 or packet.step < packet.max_hops:  # packet can still hop
            if self.address.is_share_subnetwork(packet.destination.address):  # device is in the local network
                dest_local_address = packet.destination.address[len(self.address) - 1]
                next_device_address = self.routing_table[dest_local_address][1]
                next_device = self.parent.get_subnetwork_at(next_device_address)
            else:  # device is outside the local network, send to gateway:
                gateway_address = self.parent.gateway_local_address()

                if self.address[-1] == gateway_address:  # if this is the gateway device:
                    # propagate message "upwards"
                    next_device = self.parent.get_next_gateway(packet)
                else:  # this is not the gateway device:
                    dest_local_address = gateway_address
                    next_device_address = self.routing_table[dest_local_address][1]
                    next_device = self.parent.get_subnetwork_at(next_device_address)
            if model.VERBOSE:
                print("Device %s sending packet with destination %s to device %s" %
                      (self.address, packet.destination.address, next_device.address))
            self.packets_sent += 1

            if packet.payload:
                self._activate_edge_to(other=next_device, status="malicious")
            else:
                self._activate_edge_to(other=next_device, status="active")
            packet.step += 1
            next_device.route(packet)
        else:  # packet reached its maximum amount of hops
            packet.stop_step = self.model.schedule.steps
            self.current_packets.append(packet)
            if model.VERBOSE:
                print(
                    "Packet %s going to device %s has reached maximum number of %d hops in %d steps and stopped at device %s" %
                    (packet.packet_id, packet.destination.address, packet.max_hops, packet.step, self.address))

    def _activate_edge_to(self, other, status):
        self.model.G.get_edge_data(self.master_address,
                                   other.master_address)[status] = True

    def step(self):
        self.passing_packets = 0

    def advance(self):
        i = 0
        while i < len(self.current_packets):
            packet = self.current_packets[i]
            if packet.stop_step < self.model.schedule.steps:
                self.current_packets.pop(i)
                packet.step = 0
                if model.VERBOSE:
                    print("Device %s contains packet %s .. continue routing.." % (self.address, packet.packet_id))
                self.route(packet)
            else:
                i += 1

    def __eq__(self, other):
        return self.address == other.address
