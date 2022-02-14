from core_plugins.context.typing import Context
from .config import CONFIG, UserString
import math
import nonebot

context: Context = nonebot.require("context")

class Item:
  force_show = context.Permission.MEMBER
  blacklist: set[str] = set()
  items: list["Item"] = []

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

  def register(self) -> "Item":
    Item.items.append(self)
    return self
  
  def can_show(self, current_context: int, private: bool, permission: context.Permission) -> bool:
    if self.private is not None and private != self.private:
      return False
    if not context.in_context(current_context, *self.contexts):
      return False
    if permission < self.permission:
      return False
    return self.id not in Item.blacklist

class StringItem(Item):
  def __init__(self, id: str, string: str, **kw):
    super().__init__(id, **kw)
    self.string = string

  def __call__(self) -> str:
    return self.string

class CommandItem(Item):
  commands: dict[str, "CommandItem"] = {}
  prefixes = {
    context.Permission.MEMBER: "",
    context.Permission.ADMIN: "[群管] ",
    context.Permission.OWNER: "[群主] ",
    context.Permission.SUPER: "[超管] ",
  }

  def __init__(self, name: str, aliases: list[str] = [], brief: str = "", usage: list[str] | str = "", **kw):
    super().__init__(name, **kw)
    self.name = name
    self.aliases = aliases
    if isinstance(usage, list):
      self._usage = "\n".join(usage)
    else:
      self._usage = usage
    self.brief = f"{CommandItem.prefixes[self.permission]}/{self.name}"
    if brief:
      self.brief += f" - {brief}"
  
  def register(self) -> Item:
    CommandItem.commands[self.name] = self
    for i in self.aliases:
      CommandItem.commands[i] = self
    return super().register()
  
  def __call__(self) -> str:
    return self.brief
  
  @property
  def usage(self) -> str:
    segments = [self.brief]
    if len(self._usage) == 0:
      segments.append("没有用法说明")
    else:
      segments.append(self._usage)
    if len(self.aliases) != 0:
      segments.append("该命令有以下别名：" + "、".join(self.aliases))
    return "\n".join(segments)

def add_string(id: str, string: str, **kw) -> StringItem:
  return StringItem(id, string, **kw).register()

user_string_count = 0
def add_user_string(string: str, **kw) -> StringItem:
  global user_string_count
  user_string_count += 1
  return StringItem(f"user_string_{user_string_count}", string, **kw).register()

def add_command(names: str | list[str], brief: str = "", usage: list[str] | str = "", **kw) -> CommandItem:
  if isinstance(names, str):
    name = names
    aliases = []
  else:
    name = names[0]
    aliases = names[1:]
  return CommandItem(name, aliases, brief, usage, **kw).register()

def format_page(i: int, current_context: int, private: bool, permission: context.Permission) -> str:
  show_permission = max(permission, Item.force_show)
  # show_permission = max(permission, Item.force_show) if private else Item.force_show
  vaild_items = ["使用 /帮助 <命令名> 查看详细用法"]
  if current_context == context.PRIVATE:
    vaild_items.append("请进入上下文查看群聊命令")
  # elif permission > show_permission and not private:
  #   vaild_items.append("请私聊查看高权限命令")
  vaild_items.extend(sorted(map(lambda x: x(), filter(lambda x: x.can_show(current_context, private, show_permission), Item.items))))
  pages = math.ceil(1.0 * len(vaild_items) / CONFIG.page_size)
  if i < 1 or i > pages:
    return f"页码范围从 1 到 {pages}"
  start = (i - 1) * CONFIG.page_size
  end = min(i * CONFIG.page_size, len(vaild_items))
  pageid = f"第 {i} 页，共 {pages} 页\n"
  return pageid + "\n".join(vaild_items[start:end])

def find_command(name: str, private: bool, current_context: int, permission: context.Permission) -> CommandItem | None:
  show_permission = max(permission, Item.force_show) if private else Item.force_show
  if name not in CommandItem.commands:
    return None
  command = CommandItem.commands[name]
  if command.can_show(current_context, private, show_permission):
    return command
  return None

Item.force_show = context.Permission.parse(CONFIG.force_show)
Item.blacklist.update(CONFIG.blacklist)

for command in CONFIG.user_helps:
  if isinstance(command, str):
    add_user_string(command)
  elif isinstance(command, UserString):
    add_user_string(command.string, priority=command.priority, private=command.private, contexts=command.contexts, permission=command.permission)
  else:
    add_command(command.command, command.brief, command.usage, priority=command.priority, private=command.private, contexts=command.contexts, permission=command.permission)

def add_commands():
  for plugin in nonebot.get_loaded_plugins():
    for matcher in plugin.matcher:
      if not hasattr(matcher, "__cmd__"):
        continue
      add_command(
        matcher.__cmd__,
        getattr(matcher, "__brief__", ""),
        getattr(matcher, "__doc__", ""),
        priority=getattr(matcher, "__priority__", 1 - matcher.priority),
        contexts=getattr(matcher, "__ctx__", []),
        private=getattr(matcher, "__priv__", None),
        permission=getattr(matcher, "__perm__", context.MEMBER))
