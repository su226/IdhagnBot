from typing import Literal
from typing_extensions import Self

from nonebot.matcher import Matcher
from nonebot.rule import Rule, ArgumentParser
from nonebot.typing import T_RuleChecker
import nonebot

from . import permission, context, help

class CommandBuilder:
  def __init__(self, node: str, name: str, *names: str) -> None:
    self.node = node
    self.names = [name, *names]
    self.rule_ = Rule()
    self.level_ = permission.Level.MEMBER
    self.parser_ = None

    self.brief_ = ""
    self.usage_ = ""
    self.category_ = ""
    self.help_data = help.CommonData(node=node)

  def level(self, level: Literal["member", "admin", "owner", "super"] = "member") -> Self:
    self.level_ = permission.Level.parse(level)
    self.help_data.level = self.level_
    return self

  def rule(self, rule: Rule | T_RuleChecker, *rules: Rule | T_RuleChecker) -> Self:
    self.rule_ &= rule
    for r in rules:
      self.rule_ &= r
    return self

  def in_group(self, *groups: int) -> Self:
    if not groups:
      groups = (context.ANY_GROUP,)
    self.help_data.in_group = list(groups)
    return self.rule(context.in_group_rule(*groups))

  def has_group(self, group: int, *groups: int) -> Self:
    self.help_data.has_group = [group, *groups]
    return self.rule(context.has_group_rule(group, *groups))

  def brief(self, brief: str) -> Self:
    self.brief_ = brief
    return self

  def usage(self, usage: str) -> Self:
    self.usage_ = usage
    return self

  def category(self, category: str) -> Self:
    self.category_ = category
    return self

  def shell(self, parser: ArgumentParser) -> Self:
    parser.prog = "/" + self.names[0]
    self.parser_ = parser
    self.usage_ = parser.format_help()
    return self

  def private(self, private: bool) -> Self:
    self.help_data.private = private
    return self

  def build(self) -> type[Matcher]:
    cat = help.CategoryItem.find(self.category_, True)
    cat.add(help.CommandItem(self.names, self.brief_, self.usage_, self.help_data))
    permission_ = context.build_permission(tuple(self.node.split(".")), self.level_)
    if self.parser_ is None:
      return nonebot.on_command(self.names[0], self.rule_, set(self.names[1:]), permission=permission_, _depth=1) # type: ignore
    return nonebot.on_shell_command(self.names[0], self.rule_, set(self.names[1:]), self.parser_, permission=permission_, _depth=1) # type: ignore
