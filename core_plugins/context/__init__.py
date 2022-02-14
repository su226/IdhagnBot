from dataclasses import dataclass, field
from typing import Any
from .core import PRIVATE, ANY_GROUP, get_event_context, in_context, in_context_rule, Permission, get_permission
from .commands import group_to_name
import nonebot

@dataclass
class CommonArgs:
  names: list[str] = field(default_factory=list)
  brief: str = ""
  usage: str = ""
  contexts: list[int] = field(default_factory=list)
  permission: Permission = Permission.MEMBER

exports = nonebot.export()
exports.PRIVATE = PRIVATE
exports.ANY_GROUP = ANY_GROUP
exports.MEMBER = Permission.MEMBER
exports.ADMIN = Permission.ADMIN
exports.OWNER = Permission.OWNER
exports.SUPER = Permission.SUPER
exports.Permission = Permission
exports.CommonArgs = CommonArgs
exports.get_context = get_event_context
exports.in_context = in_context
exports.in_context_rule = in_context_rule
exports.get_permission = get_permission
exports.get_group_name = lambda group: group_to_name[group]
exports.has_group = lambda group: group in group_to_name

@exports
def parse_common(data: dict, **kw: Any) -> tuple[CommonArgs, dict[str, Any]]:
  common = CommonArgs(**kw)
  if "names" in data:
    common.names = data["names"]
    if not isinstance(common.names, list):
      common.names = [common.names]
    del data["names"]
  if "brief" in data:
    common.brief = data["brief"]
    del data["brief"]
  if "usage" in data:
    common.usage = data["usage"]
    if not isinstance(common.usage, str):
      common.usage = "\n".join(common.usage)
    del data["usage"]
  if "contexts" in data:
    common.contexts = data["contexts"]
    if not isinstance(common.contexts, list):
      common.contexts = [common.contexts]
    del data["contexts"]
  if "permission" in data:
    common.permission = Permission.parse(data["permission"])
    del data["permission"]
  return common, data
