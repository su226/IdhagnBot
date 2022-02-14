from datetime import datetime
from util.config import BaseConfig, BaseModel, BaseState, Field

class Config(BaseConfig):
  __file__ = "context"
  groups: dict[int, list[str]] = Field(default_factory=dict)

class Context(BaseModel):
  group: int
  expire: datetime

class State(BaseState):
  __file__ = "context"
  contexts: dict[int, Context] = Field(default_factory=dict)

CONFIG = Config.load()
STATE = State.load()

now = datetime.now()
expired = []
for user, context in STATE.contexts.items():
  if context.expire <= now:
    expired.append(user)
for user in expired:
  del STATE.contexts[user]
