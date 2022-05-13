from typing import Pattern

from pydantic import BaseModel, Field, PrivateAttr

from util.config import BaseConfig

class GroupTarget(BaseModel):
  group: int

class UserTarget(BaseModel):
  user: int

class User(BaseModel):
  uid: int
  targets: list[GroupTarget | UserTarget]
  _name: str = PrivateAttr()
  _time: float = PrivateAttr()

class Config(BaseConfig, file="bilibili_activity"):
  ellipsis: int = 50
  interval: int = 600
  users: list[User] = Field(default_factory=list)
  ignore_regexs: list[Pattern] = Field(default_factory=list)
  ignore_forward_regexs: list[Pattern] = Field(default_factory=list)

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

class IgnoredException(Exception): pass

def check_ignore(forward: bool, content: str):
  regexs = CONFIG.ignore_forward_regexs if forward else CONFIG.ignore_regexs
  for regex in regexs:
    if regex.search(content):
      raise IgnoredException(regex)
