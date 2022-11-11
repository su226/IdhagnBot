from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Iterable, Literal, TypeVar, cast

from loguru import logger
from nonebot.adapters.onebot.v11 import Bot
from nonebot.exception import ActionFailed
from pydantic import BaseModel, Field, PrivateAttr

from util import configs, misc

Node = tuple[str, ...]


class Entry(BaseModel):
  node_str: str = Field(alias="node")
  value: bool
  expire: datetime | None = None
  context: dict[str, str] = Field(default_factory=dict)
  _node: tuple[str, ...] = PrivateAttr()

  def __init__(self, **kw: Any) -> None:
    super().__init__(**kw)
    self._node = tuple(self.node_str.split("."))

  @property
  def node(self) -> tuple[str, ...]:
    return self._node

  def matches(self, time: datetime, context: dict[str, str]) -> bool:
    if self.expire and self.expire < time:
      return False
    for k, v in self.context.items():
      if k not in context or context[k] != v:
        return False
    return True


class Role(BaseModel):
  priority: int = 0
  parents: list[str] = Field(default_factory=list)
  entries: list[Entry] = Field(default_factory=list)


@dataclass
class RoleEntry:
  role_name: str
  role: Role
  entry: Entry

  def __lt__(self, other: "RoleEntry") -> bool:
    return (-self.role.priority, self.role_name) < (-other.role.priority, other.role_name)


K = TypeVar("K")
V = TypeVar("V")


class Trie(Generic[K, V]):
  def __init__(self) -> None:
    self.data: list[V] = []
    self.children: dict[K, "Trie[K, V]"] = {}
    self.parent: "Trie[K, V]" = self
    self.depth = 0

  def get_most(self, key: Iterable[K]) -> "Trie[K, V]":
    cur = self
    for i in key:
      if i not in cur.children:
        break
      cur = cur.children[i]
    return cur

  def __setitem__(self, key: Iterable[K], value: V) -> None:
    cur = self
    for i in key:
      if i not in cur.children:
        child = Trie()
        child.parent = cur
        child.depth = cur.depth + 1
        cur.children[i] = child
        cur = child
      else:
        cur = cur.children[i]
    cur.data.append(value)

  def sort(self, recursive: bool = True) -> None:
    cast(list[Any], self.data).sort()
    if recursive:
      for i in self.children.values():
        i.sort()


class User(BaseModel):
  roles: list[str] = Field(default_factory=list)
  entries: list[Entry] = Field(default_factory=list)
  level: Literal[None, "member", "admin", "owner"] = None
  _tree: Trie[str, Entry] = PrivateAttr()

  def __init__(self, **kw: Any) -> None:
    super().__init__(**kw)
    self._tree = Trie()
    for entry in self.entries:
      self._tree[entry.node] = entry


class Command(BaseModel):
  level: Literal[None, "member", "admin", "owner"] = None


class State(BaseModel):
  roles: dict[str, Role] = Field(default_factory=dict)
  users: dict[int, User] = Field(default_factory=dict)
  commands: dict[str, Command] = Field(default_factory=dict)
  _tree: Trie[str, RoleEntry] = PrivateAttr()

  def __init__(self, **kw: Any) -> None:
    super().__init__(**kw)
    self._tree = Trie()
    for name, role in self.roles.items():
      for entry in role.entries:
        self._tree[entry.node] = RoleEntry(name, role, entry)
    self._tree.sort()
    if "default" not in self.roles:
      self.roles["default"] = Role()

  def get_command_level(self, node: Node) -> str | None:
    key = "." if not node else ".".join(node)
    if key in self.commands:
      return self.commands[key].level
    return None


CONFIG = configs.SharedConfig("permission", State)
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


def get_override_level(bot: Bot, user: int, group: int = -1) -> Level | None:
  if misc.is_superuser(bot, user):
    return Level.SUPER
  config = CONFIG()
  if user in config.users and (level := config.users[user].level) is not None:
    return Level.parse(level)
  return None


async def get_group_level(bot: Bot, user: int, group: int) -> Level | None:
  if group == -1:
    return None
  try:
    info = await bot.get_group_member_info(group_id=group, user_id=user)
  except ActionFailed:
    logger.exception(f"获取权限失败，这通常不应该发生！群聊: {group} 用户: {user}")
  else:
    return Level.parse(info["role"])
  return None


def get_node_level(node: Node, group: int = -1) -> Level | None:
  config = CONFIG()
  if (level_name := config.get_command_level(node)) is not None:
    return Level.parse(level_name)
  return None


def check(node: Node, user: int, group: int, level: Level) -> bool | None:
  config = CONFIG()
  roles: set[str] = set()
  queue: deque[str] = deque()
  user_tree = None
  if user in config.users:
    data = config.users[user]
    queue.extend(data.roles)
    user_tree = data._tree.get_most(node)
  while queue:
    i = queue.popleft()
    if i in roles:
      continue
    roles.add(i)
    queue.extend(config.roles[i].parents)
  roles.add("default")
  role_tree = config._tree.get_most(node)
  context = {
    "group": str(group),
    "level": level.key,
    "admin": str(level >= Level.ADMIN).lower(),
  }
  now = datetime.now()
  if user_tree:
    while user_tree.depth > role_tree.depth:
      for entry in user_tree.data:
        if entry.matches(now, context):
          return entry.value
      user_tree = user_tree.parent
    while role_tree.depth > user_tree.depth:
      for entry in role_tree.data:
        if entry.role_name in roles and entry.entry.matches(now, context):
          return entry.entry.value
      role_tree = role_tree.parent
  while True:
    if user_tree:
      for entry in user_tree.data:
        if entry.matches(now, context):
          return entry.value
      user_tree = user_tree.parent
    for entry in role_tree.data:
      if entry.role_name in roles and entry.entry.matches(now, context):
        return entry.entry.value
    role_tree = role_tree.parent
    if role_tree.depth == 0:
      break
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
