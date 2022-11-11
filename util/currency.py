from pydantic import BaseModel, Field

from util import configs


class State(BaseModel):
  users: dict[int, int] = Field(default_factory=dict)


STATE = configs.GroupState("currency", State)


def get_coin(group: int, user: int) -> int:
  return STATE(group).users.get(user, 0)


def set_coin(group: int, user: int, amount: int):
  state = STATE(group)
  state.users[user] = amount
  STATE.dump(group)


def add_coin(group: int, user: int, amount: int):
  state = STATE(group)
  state.users[user] = max(state.users.get(user, 0) + amount, 0)
  STATE.dump(group)
