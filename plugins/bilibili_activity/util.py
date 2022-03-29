from util.config import BaseConfig, BaseModel, Field, PrivateAttr

class GroupTarget(BaseModel):
  group: int

class UserTarget(BaseModel):
  user: int

class User(BaseModel):
  uid: int
  targets: list[GroupTarget | UserTarget]
  _name: str = PrivateAttr()
  _time: float = PrivateAttr()

class Config(BaseConfig):
  __file__ = "bilibili_activity"
  ellipsis: int = 50
  interval: int = 600
  users: list[User] = Field(default_factory=list)

CONFIG = Config.load()

groups: set[int] = set()
for user in CONFIG.users:
  for target in user.targets:
    if isinstance(target, GroupTarget):
      groups.add(target.group)

def ellipsis(content: str) -> str:
  if len(content) > CONFIG.ellipsis:
    return content[:CONFIG.ellipsis - 3] + "..."
  return content
