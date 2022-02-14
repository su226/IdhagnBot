from typing import Literal
from util.config import BaseConfig, BaseModel, Field

PermissionStr = Literal["member", "admin", "owner", "super"]

class UserCommons(BaseModel):
  priority: int = 0
  private: bool | None = None
  contexts: list[int] = Field(default_factory=list)
  permission: PermissionStr = "member"

class UserString(UserCommons):
  string: str

class UserCommand(UserCommons):
  command: list[str]
  brief: str = ""
  usage: str = ""

class Config(BaseConfig):
  __file__ = "help"
  force_show: PermissionStr = "member"
  page_size: int = 10
  blacklist: list[str] = Field(default_factory=list)
  user_helps: list[str | UserString | UserCommand] = Field(default_factory=list)

CONFIG = Config.load()
