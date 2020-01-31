from agents.agents import User
from agents.constructs import *
import model


class AttackClient(User):
    def __init__(self, activity, address, parent, model, routing_table, intention="attack"):
        super().__init__(activity, address, parent, model, routing_table)
        self.comm_table_out_size = random.randint(20, 300)
        self.comm_table_out_size = 0
        self.intention = intention

    def step(self):
        return super().step()

    def _generate_communications_table(self):
        return super()._generate_communications_table()
