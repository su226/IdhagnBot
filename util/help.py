import html
import math

from pydantic import Field

from util.config import BaseConfig, BaseModel
from util import context, permission

class CommonData(BaseModel):
  priority: int = 0
  node_str: str = Field(default="", alias="node")
  has_group: list[int] = Field(default_factory=list)
  in_group: list[int] = Field(default_factory=list)
  private: bool | None = None
  level: permission.Level = permission.Level.MEMBER

  @property
  def node(self) -> permission.Node | None:
    if not self.node_str:
      return None
    elif self.node_str == ".":
      return ()
    return tuple(self.node_str.split("."))

class ShowData(BaseModel):
  user_id: int
  current_group: int
  available_groups: list[int]
  private: bool
  level: permission.Level

class UserData(CommonData):
  category: str = ""

class UserString(UserData):
  string: str

class UserCommand(UserData):
  command: list[str]
  brief: str = ""
  usage: str = ""

class Config(BaseConfig):
  __file__ = "help"
  page_size: int = 10
  user_helps: list[str | UserString | UserCommand] = Field(default_factory=list)
  category_brief: dict[str, str] = Field(default_factory=dict)

CONFIG = Config.load()

def check_permission(data: CommonData, show: ShowData) -> bool:
  node = data.node
  if node:
    if (result := permission.check(node, show.user_id, show.current_group)) is not None:
      return result
    command_level = permission.get_node_level(node) or data.level
  else:
    command_level = data.level
  return show.level >= command_level

class Item:
  def __init__(self, data: CommonData | None):
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
      segments.append(f"在群聊中: {'、'.join('任意' if x == context.ANY_GROUP else str(x) for x in self.data.in_group)}")
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
    return True

class StringItem(Item):
  def __init__(self, string: str, data: CommonData | None = None):
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
  commands: dict[str, "CommandItem"] = {}
  prefixes = {
    permission.Level.MEMBER: "",
    permission.Level.ADMIN: "[群管] ",
    permission.Level.OWNER: "[群主] ",
    permission.Level.SUPER: "[超管] ",
  }

  def __init__(self, names: list[str] = [], brief: str = "", usage: str = "", data: CommonData | None = None):
    super().__init__(data)
    self.names = names
    self.raw_usage = usage
    self.brief = brief
    for i in self.names:
      self.commands[i] = self

  def html(self) -> str:
    if (info := super().html()):
      info = f"\n{info}"
    return f"<details id=\"{html.escape(self.names[0])}\"><summary>{html.escape(self())}</summary><pre>{html.escape(self.format(False))}{info}</pre></details>"

  def get_order(self) -> int:
    return self.data.level.value

  @staticmethod
  def find(name: str) -> "CommandItem":
    return CommandItem.commands[name]
  
  def __call__(self) -> str:
    brief = f" - {self.brief}" if self.brief else ""
    return f"{self.prefixes[self.data.level]}/{self.names[0]}{brief}"
  
  def format(self, brief: bool = True) -> str:
    segments = []
    if brief:
      segments.append(self())
    if len(self.raw_usage) == 0:
      segments.append("没有用法说明")
    else:
      segments.append(self.raw_usage)
    if len(self.names) > 1:
      segments.append("该命令有以下别名：" + "、".join(self.names[1:]))
    return "\n".join(segments)

class CategoryItem(Item):
  ROOT: "CategoryItem"

  def __init__(self, name: str, brief: str = "", data: CommonData | None = None):
    super().__init__(data)
    self.name = name
    self.brief = brief
    self.items: list[Item] = []
    self.subcategories: dict[str, "CategoryItem"] = {}
  
  def __call__(self) -> str:
    brief = f" - {self.brief}" if self.brief else ""
    return f".{self.name}{brief}"

  def html(self, details: bool = True) -> str:
    content = "".join(f"<li>{x.html()}</li>" for x in sorted(self.items, key=lambda x: (-x.data.priority, x.get_order(), x())))
    if (info := super().html()):
      content = f"<pre>{info}</pre><ul>{content}</ul>"
    else:
      content = f"<ul>{content}</ul>"
    if details:
      return f"<details><summary>{html.escape(self())}</summary>{content}</details>"
    return f"{content}"

  def get_order(self) -> int:
    return -2

  @staticmethod
  def find(path: str | list[str], create: bool = False) -> "CategoryItem":
    cur = CategoryItem.ROOT
    if isinstance(path, str):
      path = [x for x in path.split(".") if x]
    for i, name in enumerate(path, 1):
      if name not in cur.subcategories:
        if not create:
          raise KeyError(f"子分类 {'.'.join(path[:i])} 不存在")
        sub = CategoryItem(name)
        cur.add(sub)
      cur = cur.subcategories[name]
    return cur

  def add(self, item: Item):
    self.items.append(item)
    if isinstance(item, CategoryItem):
      self.subcategories[item.name] = item

  def format(self, page_id: int, show_data: ShowData) -> str:
    vaild_items = ["使用 /帮助 <命令名> 查看详细用法"]
    vaild_items.extend(x[-1] for x in sorted((-x.data.priority, x.get_order(), x())
      for x in self.items if x.can_show(show_data)))
    pages = math.ceil(len(vaild_items) / CONFIG.page_size)
    if page_id < 1 or page_id > pages:
      return f"页码范围从 1 到 {pages}"
    start = (page_id - 1) * CONFIG.page_size
    end = min(page_id * CONFIG.page_size, len(vaild_items))
    pageid = f"第 {page_id} 页，共 {pages} 页\n"
    return pageid + "\n".join(vaild_items[start:end])

CategoryItem.ROOT = CategoryItem("root")

def export_index_html() -> str:
  segments = (f"<li><a href=\"#{html.escape(command.names[0])}\">{CommandItem.prefixes[command.data.level]}{html.escape(name)}</a></li>"
    for name, command in sorted(CommandItem.commands.items(), key=lambda x: x[0]))
  return f"<ul>{''.join(segments)}</ul>"  

for item in CONFIG.user_helps:
  if isinstance(item, str):
    CategoryItem.ROOT.add(StringItem(item))
  elif isinstance(item, UserString):
    CategoryItem.find(item.category, True).add(StringItem(item.string, item))
  else:
    CategoryItem.find(item.category, True).add(CommandItem(item.command, item.brief, item.usage, item))

for path, brief in CONFIG.category_brief.items():
  CategoryItem.find(path, True).brief = brief
