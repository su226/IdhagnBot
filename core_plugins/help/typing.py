from typing import TYPE_CHECKING, Type
if TYPE_CHECKING:
  from core_plugins.context.core import Permission
  from .item import CommandItem as _CommandItem, StringItem as _StringItem

class Help:
  CommandItem: Type["_CommandItem"]
  StringItem: Type["_StringItem"]
  @staticmethod
  def add_commands(): ...
  @staticmethod
  def add_command(names: str | list[str], brief: str = "", usage: list[str] | str = [], *, priority: int = 0, contexts: list[int] | int = [], private: bool = None, permission: "Permission | str" = ...) -> "_CommandItem": ...
  @staticmethod
  def add_string(id: str, string: str, *, priority: int = 0, contexts: list[int] | int = [], private: bool = None, permission: "Permission | str" = ...) -> "_StringItem": ...
