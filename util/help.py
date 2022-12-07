import html
from typing import Callable, Dict, List, Optional, Union
from nonebot.adapters.onebot.v11 import MessageSegment

from pydantic import BaseModel, Field

from util import configs, context, permission, misc


def NOOP_CONDITION(_): return True


class CommonData(BaseModel):
  priority: int = 0
  node_str: str = Field(default="", alias="node")
  has_group: List[int] = Field(default_factory=list)
  in_group: List[int] = Field(default_factory=list)
  private: Optional[bool] = None
  level: permission.Level = permission.Level.MEMBER
  condition: Callable[["ShowData"], bool] = NOOP_CONDITION

  @property
  def node(self) -> Optional[permission.Node]:
    if not self.node_str:
      return None
    elif self.node_str == ".":
      return ()
    return tuple(self.node_str.split("."))


class ShowData(BaseModel):
  user_id: int
  current_group: int
  available_groups: List[int]
  private: bool
  level: permission.Level


class UserData(CommonData):
  category: str = ""


class UserString(UserData):
  string: str


class UserCommand(UserData):
  command: List[str]
  brief: str = ""
  usage: str = ""


class UserCategory(UserData):
  brief: str = ""


class Config(BaseModel):
  __file__ = "help"
  page_size: int = 10
  user_helps: List[Union[str, UserString, UserCommand, UserCategory]] = Field(default_factory=list)
  category_brief: Dict[str, str] = Field(default_factory=dict)


CONFIG = configs.SharedConfig("help", Config)


@CONFIG.onload()
def onload(prev: Optional[Config], curr: Config) -> None:
  if prev:
    CommandItem.remove_user_items()
    CategoryItem.ROOT.remove_user_items()
  for item in curr.user_helps:
    if isinstance(item, str):
      CategoryItem.ROOT.add(UserStringItem(item))
    elif isinstance(item, UserCategory):
      category = UserCategoryItem.find(item.category, True)
      if not isinstance(category, UserCategoryItem):
        continue
      category.brief = item.brief
      category.data = item
    elif isinstance(item, UserString):
      UserCategoryItem.find(item.category, True).add(UserStringItem(item.string, item))
    else:
      UserCategoryItem.find(item.category, True).add(
        UserCommandItem(item.command, item.brief, item.usage, item)
      )


def check_permission(data: CommonData, show: ShowData) -> bool:
  node = data.node
  if node:
    result = permission.check(node, show.user_id, show.current_group, show.level)
    if result is not None:
      return result
    command_level = permission.get_node_level(node) or data.level
  else:
    command_level = data.level
  return show.level >= command_level


class Item:
  def __init__(self, data: Optional[CommonData]):
    self.data = CommonData() if data is None else data

  def __call__(self) -> str:
    raise NotImplementedError

  def html(self) -> str:
    segments = []
    if self.data.node_str:
      segments.append(f"权限节点: {self.data.node_str}")
    if self.data.has_group:
      segments.append(f"加入群聊: {'、'.join(str(x) for x in self.data.has_group)}")
    if self.data.in_group:
      groups = '、'.join('任意' if x == context.ANY_GROUP else str(x) for x in self.data.in_group)
      segments.append(f"在群聊中: {groups}")
    if self.data.private is not None:
      segments.append(f"私聊: {'仅私聊' if self.data.private else '仅群聊'}")
    if self.data.level != permission.Level.MEMBER:
      segments.append(f"默认等级: {permission.EXPORT_LEVELS[self.data.level]}")
    if segments:
      return "\n".join(segments)
    return ""

  def get_order(self) -> int:
    return 0

  def can_show(self, data: ShowData) -> bool:
    if not check_permission(self.data, data):
      return False
    if self.data.in_group and not context.in_group(data.current_group, *self.data.in_group):
      return False
    if self.data.has_group and not any(i in self.data.has_group for i in data.available_groups):
      return False
    if self.data.private is not None and data.private != self.data.private:
      return False
    return self.data.condition(data)


class StringItem(Item):
  def __init__(self, string: str, data: Optional[CommonData] = None):
    super().__init__(data)
    self.string = string

  def __call__(self) -> str:
    return self.string

  def html(self) -> str:
    summary = html.escape(self.string)
    if (details := super().html()):
      return f"<details><summary>{summary}</summary>{details}</details>"
    return summary

  def get_order(self) -> int:
    return -1


class CommandItem(Item):
  commands: Dict[str, "CommandItem"] = {}
  prefixes = {
    permission.Level.MEMBER: "",
    permission.Level.ADMIN: "[群管] ",
    permission.Level.OWNER: "[群主] ",
    permission.Level.SUPER: "[超管] ",
  }
  prefixes2 = {
    permission.Level.MEMBER: "",
    permission.Level.ADMIN: "群管 | ",
    permission.Level.OWNER: "群主 | ",
    permission.Level.SUPER: "超管 | ",
  }

  def __init__(
    self, names: List[str] = [], brief: str = "", usage: Union[str, Callable[[], str]] = "",
    data: Optional[CommonData] = None
  ) -> None:
    super().__init__(data)
    self.names = names
    self.raw_usage = usage
    self.brief = brief
    for i in self.names:
      if i in self.commands:
        raise ValueError(f"重复的命令名: {i}")
      self.commands[i] = self

  def html(self) -> str:
    if (info := super().html()):
      info = f"\n{info}"
    return (
      f"<details id=\"{html.escape(self.names[0])}\"><summary>{html.escape(self())}</summary>"
      f"<pre>{html.escape(self.format(False))}{info}</pre></details>"
    )

  def get_order(self) -> int:
    return self.data.level.order

  @staticmethod
  def find(name: str) -> "CommandItem":
    return CommandItem.commands[name]

  def __call__(self) -> str:
    brief = f" - {self.brief}" if self.brief else ""
    return f"{self.prefixes[self.data.level]}/{self.names[0]}{brief}"

  def format(self, brief: bool = True) -> str:
    segments = []
    if brief:
      segments.append(f"「{self.prefixes2[self.data.level]}{self.names[0]}」{self.brief}")
    if isinstance(self.raw_usage, str):
      raw_usage = self.raw_usage
    else:
      raw_usage = self.raw_usage()
    if len(raw_usage) == 0:
      segments.append("没有用法说明")
    else:
      segments.append(raw_usage)
    if len(self.names) > 1:
      segments.append("该命令有以下别名：" + "、".join(self.names[1:]))
    return "\n".join(segments)

  @staticmethod
  def remove_user_items() -> None:
    remove_keys: List[str] = []
    for k, v in CommandItem.commands.items():
      if isinstance(v, UserCommandItem):
        remove_keys.append(k)
    for i in remove_keys:
      del CommandItem.commands[i]


class CategoryItem(Item):
  ROOT: "CategoryItem"

  def __init__(self, name: str, brief: str = "", data: Optional[CommonData] = None):
    super().__init__(data)
    self.name = name
    self.brief = brief
    self.items: List[Item] = []
    self.subcategories: Dict[str, "CategoryItem"] = {}

  def __call__(self) -> str:
    brief = f" - {self.brief}" if self.brief else ""
    return f"📁{self.name}{brief}"

  def html(self, details: bool = True) -> str:
    content = "".join(f"<li>{x.html()}</li>" for x in sorted(
      self.items, key=lambda x: (-x.data.priority, x.get_order(), x())))
    if (info := super().html()):
      content = f"<pre>{info}</pre><ul>{content}</ul>"
    else:
      content = f"<ul>{content}</ul>"
    if details:
      return f"<details><summary>{html.escape(self())}</summary>{content}</details>"
    return f"{content}"

  def get_order(self) -> int:
    return -2

  @classmethod
  def find(
    cls, path: Union[str, List[str]], create: bool = False, check: Optional[ShowData] = None
  ) -> "CategoryItem":
    cur = CategoryItem.ROOT
    if isinstance(path, str):
      path = [x for x in path.split(".") if x]
    for i, name in enumerate(path, 1):
      if name not in cur.subcategories:
        if not create:
          raise KeyError(f"子分类 {'.'.join(path[:i])} 不存在")
        sub = cls(name)
        cur.add(sub)
        cur = sub
      else:
        cur = cur.subcategories[name]
        if check and not cur.can_show(check):
          raise ValueError(f"子分类 {'.'.join(path[:i])} 不能显示")
    return cur

  def add(self, item: Item):
    if isinstance(item, CategoryItem):
      if item.name in self.subcategories:
        raise ValueError(f"重复的子分类名: {item.name}")
      self.subcategories[item.name] = item
    self.items.append(item)

  def format(
    self, show_data: ShowData, path: List[str], bot_id: int, bot_name: str
  ) -> List[MessageSegment]:
    vaild_items = [x[-2:] for x in sorted(
      (-x.data.priority, x.get_order(), x(), x)
      for x in self.items if x.can_show(show_data)
    )]
    config = CONFIG()
    has_command = False
    has_category = False
    nodes: List[MessageSegment] = []
    for chunk in misc.chunked(vaild_items, config.page_size):
      lines: List[str] = []
      for formatted, item in chunk:
        if isinstance(item, CommandItem):
          has_command = True
        elif isinstance(item, CategoryItem):
          has_category = True
        lines.append(formatted)
      nodes.append(misc.forward_node(bot_id, bot_name, "\n".join(lines)))
    header_lines: List[str] = []
    if has_command:
      header_lines.append(
        "ℹ 斜线「/」开头的是命令，发送「/help <命令名>」查看，"
        "比如假设有「/某个命令」，就需要发送「/help 某个命令」来查看"
      )
    if has_category:
      path_str = "".join(f" {i}" for i in path)
      header_lines.append(
        f"ℹ 文件夹「📁」开头的是分类，发送「/help {path_str}<分类名>」查看，"
        f"比如假设有「📁某个分类」，就需要发送「/help {path_str}某个分类」来查看"
      )
    if header_lines:
      nodes.insert(0, misc.forward_node(bot_id, bot_name, "\n".join(header_lines)))
    return nodes

  def remove_user_items(self) -> None:
    self.items = [item for item in self.items if not isinstance(item, UserItem)]
    remove_keys: List[str] = []
    for k, v in self.subcategories.items():
      if isinstance(v, UserCategoryItem):
        remove_keys.append(k)
      else:
        v.remove_user_items()
    for k in remove_keys:
      del self.subcategories[k]


CategoryItem.ROOT = CategoryItem("root")


class UserItem(Item):
  pass


class UserStringItem(StringItem, UserItem):
  pass


class UserCommandItem(CommandItem, UserItem):
  pass


class UserCategoryItem(CategoryItem, UserItem):
  pass


def export_index_html() -> str:
  segments = (
    f"<li><a href=\"#{html.escape(command.names[0])}\">"
    f"{CommandItem.prefixes[command.data.level]}{html.escape(name)}</a></li>"
    for name, command in sorted(CommandItem.commands.items(), key=lambda x: x[0])
  )
  return f"<ul>{''.join(segments)}</ul>"
