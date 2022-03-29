from util.config import BaseState, Field

class State(BaseState):
  __file__ = "coin"
  groups: dict[int, dict[int, int]] = Field(default_factory=dict)

STATE = State.load()

def get_coin(group: int, user: int) -> int:
  return STATE.groups.get(group, {}).get(user, 0)

def set_coin(group: int, user: int, amount: int):
  if group not in STATE.groups:
    STATE.groups[group] = {}
  STATE.groups[group][user] = amount
  STATE.dump()

def add_coin(group: int, user: int, amount: int):
  if group not in STATE.groups:
    STATE.groups[group] = {}
  group_data = STATE.groups[group]
  if user not in group_data:
    group_data[user] = 0
  group_data[user] += amount
  STATE.dump()
