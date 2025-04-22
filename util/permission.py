from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import (
  Any, Deque, Dict, Iterable, List, Literal, Mapping, Optional, Set, Tuple, TypeVar, Union, cast,
)

from loguru import logger
from nonebot.adapters.onebot.v11 import Bot
from nonebot.exception import ActionFailed
from pydantic import BaseModel, Field, PrivateAttr
from pygtrie import StringTrie

from util import configs, misc

Node = Tuple[str, ...]


class Entry(BaseModel):
  node_str: str = Field(alias="node")
  value: bool
  expire: Optional[datetime] = None
  context: Dict[str, str] = Field(default_factory=dict)
  _node: Tuple[str, ...] = PrivateAttr()

  def __init__(self, **kw: Any) -> None:
    super().__init__(**kw)
    self._node = tuple(filter(None, self.node_str.split(".")))

  @property
  def node(self) -> Tuple[str, ...]:
    return self._node

  def matches(self, time: datetime, context: Mapping[str, Optional[str]]) -> bool:
    if self.expire and self.expire < time:
      return False
    for k, v in self.context.items():
      if k not in context or context[k] != v:
        return False
    return True


class Role(BaseModel):
  priority: int = 0
  parents: List[str] = Field(default_factory=list)
  entries: List[Entry] = Field(default_factory=list)


@dataclass
class RoleEntry:
  role_name: str
  role: Role
  entry: Entry

  def __lt__(self, other: "RoleEntry") -> bool:
    return (-self.role.priority, self.role_name) < (-other.role.priority, other.role_name)


K = TypeVar("K")
V = TypeVar("V")


class NodeTrie(StringTrie):
  def __init__(self, *args: Any, **kw: Any):
    super().__init__(separator=".", *args, **kw)

  def _path_from_key(self, key: Union[str, Node]) -> Iterable[str]:
    if isinstance(key, str):
      return key.split(self._separator)
    return key


class User(BaseModel):
  roles: List[str] = Field(default_factory=list)
  entries: List[Entry] = Field(default_factory=list)
  level: Literal[None, "member", "admin", "owner"] = None
  _tree: NodeTrie = PrivateAttr()

  def __init__(self, **kw: Any) -> None:
    super().__init__(**kw)
    self._tree = NodeTrie()
    for entry in self.entries:
      cast(List[Entry], self._tree.setdefault(entry.node, [])).append(entry)


class Command(BaseModel):
  level: Literal[None, "member", "admin", "owner"] = None


class State(BaseModel):
  roles: Dict[str, Role] = Field(default_factory=dict)
  users: Dict[int, User] = Field(default_factory=dict)
  commands: Dict[str, Command] = Field(default_factory=dict)
  _tree: NodeTrie = PrivateAttr()

  def __init__(self, **kw: Any) -> None:
    super().__init__(**kw)
    self._tree = NodeTrie()
    for name, role in self.roles.items():
      for entry in role.entries:
        entries = cast(List[RoleEntry], self._tree.setdefault(entry.node, []))
        entries.append(RoleEntry(name, role, entry))
    for entries in self._tree.itervalues():
      cast(List[RoleEntry], entries).sort()
    if "default" not in self.roles:
      self.roles["default"] = Role()

  def get_command_level(self, node: Node) -> Optional[str]:
    key = "." if not node else ".".join(node)
    if key in self.commands:
      return self.commands[key].level
    return None


CONFIG = configs.SharedConfig("permission", State)
LEVELS: Dict[str, "Level"] = {}


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


def get_override_level(user: int) -> Optional[Level]:
  if misc.is_superuser(user):
    return Level.SUPER
  config = CONFIG()
  if user in config.users and (level := config.users[user].level) is not None:
    return Level.parse(level)
  return None


async def get_group_level(bot: Bot, user: int, group: int) -> Optional[Level]:
  if group == -1:
    return None
  try:
    info = await bot.get_group_member_info(group_id=group, user_id=user)
  except ActionFailed:
    logger.exception(f"获取权限失败，这通常不应该发生！群聊: {group} 用户: {user}")
  else:
    return Level.parse(info["role"])
  return None


def get_node_level(node: Node, group: int = -1) -> Optional[Level]:
  config = CONFIG()
  if (level_name := config.get_command_level(node)) is not None:
    return Level.parse(level_name)
  return None


def walk_most(trie: NodeTrie, key: Node) -> Iterable[NodeTrie._Step]:
  try:
    yield from trie.walk_towards(key)
  except KeyError:
    pass


def check(
  node: Node, user: int, group: int, level: Level, prefix: Optional[str] = None,
) -> Optional[bool]:
  config = CONFIG()
  roles: Set[str] = set()
  queue: Deque[str] = deque()
  EMPTY = []
  if user in config.users:
    data = config.users[user]
    queue.extend(data.roles)
    user_steps = [cast(List[Entry], x.get(EMPTY)) for x in walk_most(data._tree, node)]
  else:
    user_steps = []
  while queue:
    i = queue.popleft()
    if i in roles:
      continue
    roles.add(i)
    queue.extend(config.roles[i].parents)
  roles.add("default")
  role_steps = [cast(List[RoleEntry], x.get(EMPTY)) for x in walk_most(config._tree, node)]
  len_diff = len(user_steps) - len(role_steps)
  if len_diff < 0:
    user_steps += [EMPTY] * -len_diff
  else:
    role_steps += [EMPTY] * len_diff
  context = {
    "group": str(group),
    "level": level.key,
    "admin": str(level >= Level.ADMIN).lower(),
    "prefix": prefix,
  }
  now = datetime.now()
  for user_step, role_step in zip(reversed(user_steps), reversed(role_steps)):
    if user_step:
      for entry in user_step:
        if entry.matches(now, context):
          return entry.value
    if role_step:
      for entry in role_step:
        if entry.role_name in roles and entry.entry.matches(now, context):
          return entry.entry.value
  return None


EXPORT_LEVELS: Dict[Level, str] = {
  Level.MEMBER: "群员",
  Level.ADMIN: "群管",
  Level.OWNER: "群主",
  Level.SUPER: "超管",
}
EXPORT_NODES: List[Tuple[Node, Level]] = []


def register_for_export(node: Node, level: Level):
  EXPORT_NODES.append((node, level))


def export_html() -> str:
  EXPORT_NODES.sort(key=lambda x: x[0])
  content = "".join(
    f"<li>[{EXPORT_LEVELS[level]}] {'.'.join(node)}</li>" for node, level in EXPORT_NODES)
  return f"<ul>{content}</ul>"
