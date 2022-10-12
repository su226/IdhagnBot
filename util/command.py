import shlex
from typing import Callable, Literal

import nonebot
from nonebot.adapters.onebot.v11 import Message
from nonebot.consts import SHELL_ARGS, SHELL_ARGV
from nonebot.exception import ParserExit
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.rule import ArgumentParser, Rule
from nonebot.typing import T_RuleChecker, T_State
from typing_extensions import Self

from . import context, help, permission


class ShellCommandRule:
  # 修改自 nonebot.rule.ShellCommandRule
  # 特殊处理不是纯文本的消息段，以及 shlex 抛出 ValueError 的情况
  __slots__ = "parser",

  def __init__(self, parser: ArgumentParser):
    self.parser = parser

  async def __call__(self, state: T_State, msg: Message | None = CommandArg()) -> bool:
    if msg is None:  # 去掉这里虽然不影响功能，但 DEBUG 日志等级下会刷屏
      return False
    try:
      argv = self.split(msg)
      state[SHELL_ARGV] = argv
    except ValueError as e:
      state[SHELL_ARGV] = []
      state[SHELL_ARGS] = ParserExit(127, "解析命令行参数失败：" + str(e))
      return True
    try:
      args = self.parser.parse_args(argv)
      state[SHELL_ARGS] = args
    except ParserExit as e:
      state[SHELL_ARGS] = e
    return True

  @staticmethod
  def split(msg: Message) -> list[str]:
    args: list[str] = []
    for seg in msg:
      if seg.is_text():
        args.extend(shlex.split(str(seg)))
      else:
        args.append(str(seg))
    return args


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

  def shell(self, parser: ArgumentParser, set_prog: bool = True) -> Self:
    if set_prog:
      parser.prog = "/" + self.names[0]
    self.rule(ShellCommandRule(parser))
    if not self.usage_:
      self.usage_ = parser.format_help()
    return self

  def private(self, private: bool) -> Self:
    self.help_data.private = private
    return self

  def help_condition(self, condition: Callable[[help.ShowData], bool]) -> Self:
    self.help_data.condition = condition
    return self

  def build(self) -> type[Matcher]:
    cat = help.CategoryItem.find(self.category_, True)
    cat.add(help.CommandItem(self.names, self.brief_, self.usage_, self.help_data))
    permission_ = context.build_permission(tuple(self.node.split(".")), self.level_)
    return nonebot.on_command(
      self.names[0], self.rule_, set(self.names[1:]), permission=permission_,
      _depth=1)  # type: ignore
