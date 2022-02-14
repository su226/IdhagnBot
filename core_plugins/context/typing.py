from typing import TYPE_CHECKING, Any, Literal, Type
from nonebot.adapters import Bot, Event
from nonebot.rule import Rule
if TYPE_CHECKING:
  from . import CommonArgs as _CommonArgs
  from .core import Permission as _Permission

class Context:
  PRIVATE: Literal[-1]
  ANY_GROUP: Literal[-2]
  MEMBER: "Literal[_Permission.MEMBER]"
  ADMIN: "Literal[_Permission.ADMIN]"
  OWNER: "Literal[_Permission.OWNER]"
  SUPER: "Literal[_Permission.SUPER]"
  Permission: Type["_Permission"]
  CommonArgs: Type["_CommonArgs"]
  @staticmethod
  def get_context(event: Event) -> int: ...
  @staticmethod
  def in_context(context: int, *contexts: int) -> bool: ...
  @staticmethod
  def in_context_rule(*contexts: int) -> Rule: ...
  @staticmethod
  async def get_permission(bot: Bot, event: Event) -> "_Permission": ...
  @staticmethod
  def get_group_name(group: int) -> str: ...
  @staticmethod
  def has_group(group: int) -> bool: ...
  @staticmethod
  def parse_common(data: dict, **kw: Any) -> tuple["_CommonArgs", dict[str, Any]]: ...
