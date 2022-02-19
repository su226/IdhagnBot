from typing import Literal
from util.config import BaseConfig, BaseModel, Field
from util import context
import math
import nonebot

class UserCommons(BaseModel):
  category: str = ""
  priority: int = 0
  private: bool | None = None
  contexts: list[int] = Field(default_factory=list)
  permission: context.Permission = context.Permission.MEMBER

class UserString(UserCommons):
  string: str

class UserCommand(UserCommons):
  command: list[str]
  brief: str = ""
  usage: str = ""

class Config(BaseConfig):
  __file__ = "help"
  force_show: context.Permission = context.Permission.MEMBER
  page_size: int = 10
  blacklist: set[str] = Field(default_factory=set)
  user_helps: list[str | UserString | UserCommand] = Field(default_factory=list)
  category_brief: dict[str, str] = Field(default_factory=dict)

CONFIG = Config.load()

class Item:
  def __init__(self, id: str, priority: int = 0, contexts: list[int] | int = [], private: bool = None, permission: context.Permission | str = context.Permission.MEMBER):
    self.id = id
    self.priority = priority
    self.private = private
    if isinstance(contexts, int):
      self.contexts = [contexts]
    else:
      self.contexts = contexts
    if isinstance(permission, str):
      self.permission = context.Permission.parse(permission)
    else:
      self.permission = permission

  def __call__(self) -> str:
    raise NotImplementedError

  def register(self):
    return self

  def get_order(self) -> int:
    return self.priority
  
  def can_show(self, current_context: int, private: bool, permission: context.Permission) -> bool:
    if self.private is not None and private != self.private:
      return False
    if not context.in_context(current_context, *self.contexts):
      return False
    if permission < self.permission:
      return False
    return self.id not in CONFIG.blacklist

class StringItem(Item):
  def __init__(self, id: str, string: str, **kw):
    super().__init__(id, **kw)
    self.string = string

  def __call__(self) -> str:
    return self.string

  def get_order(self) -> int:
    return -1

class CommandItem(Item):
  commands: dict[str, "CommandItem"] = {}
  prefixes = {
    context.Permission.MEMBER: "",
    context.Permission.ADMIN: "[群管] ",
    context.Permission.OWNER: "[群主] ",
    context.Permission.SUPER: "[超管] ",
  }

  def __init__(self, names: list[str] = [], brief: str = "", usage: str = "", **kw):
    super().__init__(names[0], **kw)
    self.names = names
    self._usage = usage
    self.brief = brief
  
  def register(self) -> "CommandItem":
    for i in self.names:
      CommandItem.commands[i] = self
    return super().register()

  @staticmethod
  def find(name: str, private: bool, current_context: int, permission: context.Permission) -> "CommandItem | None":
    if name in CommandItem.commands:
      item = CommandItem.commands[name]
      if item.can_show(current_context, private, max(permission, CONFIG.force_show)):
        return item
    return None
  
  def __call__(self) -> str:
    brief = ""
    if self.brief:
      brief = f" - {self.brief}"
    return f"{CommandItem.prefixes[self.permission]}/{self.names[0]}{brief}"
  
  @property
  def usage(self) -> str:
    segments = [f"{CommandItem.prefixes[self.permission]}{self.names[0]}"]
    if self.brief:
      segments[0] += f" - {self.brief}"
    if len(self._usage) == 0:
      segments.append("没有用法说明")
    else:
      segments.append(self._usage)
    if len(self.names) > 1:
      segments.append("该命令有以下别名：" + "、".join(self.names[1:]))
    return "\n".join(segments)

class CategoryItem(Item):
  ROOT: "CategoryItem"

  def __init__(self, name: str, brief: str = "", **kw):
    super().__init__(name, **kw)
    self.brief = brief
    self.items: list[Item] = []
    self.items_dict: dict[str, Item] = {}
    self.string_count = 0
  
  def __call__(self) -> str:
    brief = ""
    if self.brief:
      brief = f" - {self.brief}"
    return f".{self.id}{brief}"

  def get_order(self) -> int:
    return -2

  @staticmethod
  def find(path: str | list[str], create: bool = False) -> "CategoryItem":
    cur = CategoryItem.ROOT
    if isinstance(path, str):
      path = [x for x in path.split(".") if x]
    for i, id in enumerate(path, 1):
      if id not in cur.items_dict:
        if not create:
          raise KeyError(f"子分类 {'.'.join(path[:i])} 不存在")
        sub = CategoryItem(id)
        cur.items.append(sub)
        cur.items_dict[id] = sub
      cur = cur.items_dict[id]
      if not isinstance(cur, CategoryItem):
        raise TypeError(f"{'.'.join(path[:i])} 不是一个子分类")
    return cur

  def add_item(self, item: Item):
    if item.id in self.items_dict:
      raise KeyError(f"已有ID为\"{item.id}\"的帮助项")
    self.items.append(item)
    self.items_dict[item.id] = item
    return item.register()

  def get_item(self, name: str, private: bool, current_context: int, permission: context.Permission) -> Item | None:
    if name in self.items_dict:
      item = self.items_dict[name]
      if item.can_show(current_context, private, max(permission, CONFIG.force_show)):
        return item
    return None

  def add_string(self, string: str, **kw) -> StringItem:
    self.string_count += 1
    return self.add_item(StringItem(f"string_{self.string_count}", string, **kw))

  def add_command(self, names: str | list[str], brief: str = "", usage: list[str] | str = "", **kw) -> CommandItem:
    if isinstance(names, str):
      names = [names]
    return self.add_item(CommandItem(names, brief, usage, **kw))

  def format_page(self, page_id: int, current_context: int, private: bool, permission: context.Permission) -> str:
    permission = max(permission, CONFIG.force_show)
    vaild_items = ["使用 /帮助 <命令名> 查看详细用法"]
    if current_context == context.PRIVATE:
      vaild_items.append("请进入上下文查看群聊命令")
    vaild_items.extend(x[-1] for x in sorted((-x.priority, x.get_order(), x())
      for x in self.items if x.can_show(current_context, private, permission)))
    pages = math.ceil(len(vaild_items) / CONFIG.page_size)
    if page_id < 1 or page_id > pages:
      return f"页码范围从 1 到 {pages}"
    start = (page_id - 1) * CONFIG.page_size
    end = min(page_id * CONFIG.page_size, len(vaild_items))
    pageid = f"第 {page_id} 页，共 {pages} 页\n"
    return pageid + "\n".join(vaild_items[start:end])

CategoryItem.ROOT = CategoryItem("root")

for item in CONFIG.user_helps:
  if isinstance(item, str):
    CategoryItem.ROOT.add_string(item)
  elif isinstance(item, UserString):
    CategoryItem.find(item.category, True).add_string(item.string, priority=item.priority, private=item.private, contexts=item.contexts, permission=item.permission)
  else:
    CategoryItem.find(item.category, True).add_command(item.command, item.brief, item.usage, priority=item.priority, private=item.private, contexts=item.contexts, permission=item.permission)

for path, brief in CONFIG.category_brief.items():
  CategoryItem.find(path, True).brief = brief

def add_all_from_plugins():
  for plugin in nonebot.get_loaded_plugins():
    for name, data in getattr(plugin.module, "__cat__", {}).items():
      category = CategoryItem.find(name, True)
      category.brief = data.get("brief", category.brief)
      category.priority = data.get("priority", category.priority)
      category.private = data.get("private", category.private)
      category.contexts = data.get("contexts", category.contexts)
      category.permission = data.get("permission", category.permission)
      for extra in data.get("extras", []):
        try:
          item = UserString.parse_obj(extra)
        except:
          pass
        else:
          category.add_string(item.string, priority=item.priority, private=item.private, contexts=item.contexts, permission=item.permission)
          continue
        try:
          item = UserCommand.parse_obj(extra)
        except:
          pass
        else:
          category.add_command(item.command, item.brief, item.usage, priority=item.priority, private=item.private, contexts=item.contexts, permission=item.permission)
          continue
        if isinstance(extra, str):
          category.add_string(extra)
        else:
          raise ValueError("无效的帮助项")
    for matcher in plugin.matcher:
      if not hasattr(matcher, "__cmd__"):
        continue
      CategoryItem.find(getattr(matcher, "__cat__", ""), True).add_command(
        matcher.__cmd__,
        getattr(matcher, "__brief__", ""),
        getattr(matcher, "__doc__", ""),
        priority=getattr(matcher, "__priority__", 1 - matcher.priority),
        contexts=getattr(matcher, "__ctx__", []),
        private=getattr(matcher, "__priv__", None),
        permission=getattr(matcher, "__perm__", context.Permission.MEMBER))
