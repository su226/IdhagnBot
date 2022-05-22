from enum import Enum
from typing import Any, Literal

from loguru import logger
from nonebot.adapters.onebot.v11 import Adapter, Bot
from nonebot.exception import ActionFailed
from pydantic import BaseModel, Field

from .config_v2 import GroupState, SharedState

Node = tuple[str, ...]


class Entry(BaseModel):
  node_str: str = Field(alias="node")
  value: bool

  @property
  def node(self) -> Node:
    if self.node_str == ".":
      return ()
    return tuple(self.node_str.split("."))


class Role(BaseModel):
  priority: int = 0
  parents: list[str] = Field(default_factory=list)
  entries: list[Entry] = Field(default_factory=list)


class User(BaseModel):
  roles: list[str] = Field(default_factory=list)
  entries: list[Entry] = Field(default_factory=list)
  level: Literal[None, "member", "admin", "owner"] = None


class Command(BaseModel):
  level: Literal[None, "member", "admin", "owner"] = None


class State(BaseModel):
  roles: dict[str, Role] = Field(default_factory=dict)
  users: dict[int, User] = Field(default_factory=dict)
  commands: dict[str, Command] = Field(default_factory=dict)

  def get_role(self, name: str) -> Role:
    if name == "default" and name not in self.roles:
      self.roles[name] = Role()
    return self.roles[name]

  def get_command_level(self, node: Node) -> str | None:
    key = "." if not node else ".".join(node)
    if key in self.commands:
      return self.commands[key].level
    return None


SHARED_STATE = SharedState("permission_override", State)
GROUP_STATE = GroupState("permission", State)
ADAPTER_NAME = Adapter.get_name().split(None, 1)[0].lower()
LEVELS: dict[str, "Level"] = {}


class Level(Enum):
  MEMBER = "member", 0
  ADMIN = "admin", 1
  OWNER = "owner", 2
  SUPER = "super", 3

  def __init__(self, key: str, order: int) -> None:
    self.key = key
    self.order = order
    LEVELS[key] = self

  def __ge__(self, other: object) -> bool:
    if isinstance(other, Level):
      return self.order >= other.order
    return NotImplemented

  def __gt__(self, other: object) -> bool:
    if isinstance(other, Level):
      return self.order > other.order
    return NotImplemented

  def __le__(self, other: object) -> bool:
    if isinstance(other, Level):
      return self.order <= other.order
    return NotImplemented

  def __lt__(self, other: object) -> bool:
    if isinstance(other, Level):
      return self.order < other.order
    return NotImplemented

  @classmethod
  def parse(cls, value: str) -> "Level":
    return LEVELS[value]


def tuple_startswith(value: tuple[Any, ...], prefix: tuple[Any, ...]) -> bool:
  return len(value) >= len(prefix) and value[:len(prefix)] == prefix


def check_in(node: Node, state: State, user: int) -> bool | None:
  entries: list[list[Entry]] = [[] for _ in range(len(node))]
  if user in state.users:
    data = state.users[user]
    role_names = set(data.roles)
    roles = [state.get_role(i) for i in role_names]
    for entry in data.entries:
      if tuple_startswith(node, entry.node):
        entries[len(node) - len(entry.node)].append(entry)
  else:
    role_names = set()
    roles = []
  for role in roles:
    for name in role.parents:
      if name not in role_names:
        role_names.add(name)
        roles.append(state.get_role(name))
  if "default" not in role_names:
    roles.append(state.get_role("default"))
  roles.sort(key=lambda x: x.priority, reverse=True)
  for role in roles:
    for entry in role.entries:
      if tuple_startswith(node, entry.node):
        entries[len(node) - len(entry.node)].append(entry)
  for e in entries:
    for e2 in e:
      # TODO: 如果有需求，增加condition，比如阻止某个用户在特定群使用某个命令
      return e2.value
  return None


def check(node: Node, user: int, group: int = 1) -> bool | None:
  shared_state = SHARED_STATE()
  if (result := check_in(node, shared_state, user)) is not None:
    return result
  if group != -1:
    group_state = GROUP_STATE(group)
    if (result := check_in(node, group_state, user)) is not None:
      return result
  return None


def is_superuser(bot: Bot, user: int) -> bool:
  return f"{ADAPTER_NAME}:{user}" in bot.config.superusers or str(user) in bot.config.superusers


def get_override_level(bot: Bot, user: int, group: int = -1) -> Level | None:
  if is_superuser(bot, user):
    return Level.SUPER
  state = SHARED_STATE()
  if user in state.users and (level := state.users[user].level) is not None:
    return Level.parse(level)
  if group != -1:
    state = GROUP_STATE(group)
    if user in state.users and (level := state.users[user].level) is not None:
      return Level.parse(level)
  return None


async def get_group_level(bot: Bot, user: int, group: int) -> Level | None:
  try:
    info = await bot.get_group_member_info(group_id=group, user_id=user)
  except ActionFailed:
    logger.exception(f"获取权限失败，这通常不应该发生！群聊: {group} 用户: {user}")
  else:
    return Level.parse(info["role"])
  return None


def get_node_level(node: Node, group: int = -1) -> Level | None:
  if (level_name := SHARED_STATE().get_command_level(node)) is not None:
    return Level.parse(level_name)
  elif group != -1 and (level_name := GROUP_STATE(group).get_command_level(node)) is not None:
    return Level.parse(level_name)
  return None


EXPORT_LEVELS: dict[Level, str] = {
  Level.MEMBER: "群员",
  Level.ADMIN: "群管",
  Level.OWNER: "群主",
  Level.SUPER: "超管",
}
EXPORT_NODES: list[tuple[Node, Level]] = []


def register_for_export(node: Node, level: Level):
  EXPORT_NODES.append((node, level))


def export_html() -> str:
  EXPORT_NODES.sort(key=lambda x: x[0])
  content = "".join(
    f"<li>[{EXPORT_LEVELS[level]}] {'.'.join(node)}</li>" for node, level in EXPORT_NODES)
  return f"<ul>{content}</ul>"
