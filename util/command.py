import asyncio
import shlex
from collections import deque
from typing import Any, Callable, Literal

import nonebot
from apscheduler.job import Job
from nonebot.adapters.onebot.v11 import Message
from nonebot.consts import SHELL_ARGS, SHELL_ARGV
from nonebot.exception import ParserExit
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, ShellCommandArgs
from nonebot.rule import ArgumentParser, Rule
from nonebot.typing import T_RuleChecker, T_State
from typing_extensions import Self

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from . import context, help, permission

driver = nonebot.get_driver()


class ShellCommandRule:
  # 修改自 nonebot.rule.ShellCommandRule
  # 特殊处理不是纯文本的消息段，以及 shlex 抛出 ValueError 的情况
  __slots__ = "prog", "parser"

  def __init__(self, prog: str, parser: ArgumentParser):
    self.prog = prog
    self.parser = parser

  async def __call__(self, state: T_State, msg: Message | None = CommandArg()) -> bool:
    if msg is None:  # 去掉 None 虽然不影响功能，但 DEBUG 日志等级下会刷屏
      return False
    try:
      argv = self.split(msg)
      state[SHELL_ARGV] = argv
    except ValueError as e:
      state[SHELL_ARGV] = []
      state[SHELL_ARGS] = ParserExit(127, "解析命令行参数失败：" + str(e))
      return True
    self.parser.prog = self.prog
    setattr(self.parser, "_message", "")
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


def add_reject_handler(matcher: type[Matcher]) -> None:
  async def handler(args: ParserExit = ShellCommandArgs()) -> None:
    await matcher.finish(args.message)
  matcher.handle()(handler)


class TokenBucket:
  def __init__(self, capacity: int, frequency: float | None) -> None:
    self.capacity = capacity
    self.frequency = 1 / capacity if frequency is None else frequency
    self.tokens = capacity
    self.queue: deque[asyncio.Future[None]] = deque()
    self.job: Job | None = None

  async def acquire(self) -> None:
    if not self.job:
      self.job = scheduler.add_job(self._generate, "interval", seconds=self.frequency)
    if self.tokens > 0:
      self.tokens -= 1
      return
    future = asyncio.get_running_loop().create_future()
    self.queue.append(future)
    await future

  def _generate(self) -> None:
    if self.queue:
      future = self.queue.popleft()
      future.set_result(None)
    else:
      self.tokens += 1
      if self.tokens >= self.capacity and self.job:
        self.job.remove()
        self.job = None

  def estimate(self) -> float:
    if self.tokens > 0:
      return 0
    return (len(self.queue) + 1) * self.frequency


def add_throttle_handler(
  matcher: type[Matcher], name: str, capacity: int, frequency: float | None
) -> None:
  async def handle_throttle():
    estimated = token.estimate()
    if estimated >= 60:
      await matcher.finish(f"当前使用 /{name} 的人数过多，请稍后再试。")
    if estimated >= 10:
      await matcher.send(f"当前使用 /{name} 的人数较多，请等待大约 {int(estimated)} 秒。")
    await token.acquire()

  token = TokenBucket(capacity, frequency)
  matcher.handle()(handle_throttle)


class CommandBuilder:
  def __init__(self, node: str, name: str, *names: str) -> None:
    self.node = node
    self.names = [name, *names]
    self._rule = Rule()
    self._level = permission.Level.MEMBER
    self._auto_reject = False
    self._state: dict[str, Any] = {}

    self._capacity = 0
    self._frequency = None

    self._brief = ""
    self._usage = ""
    self._category = ""
    self.help_data = help.CommonData(node=node)

  def level(self, level: Literal["member", "admin", "owner", "super"] = "member") -> Self:
    self._level = permission.Level.parse(level)
    self.help_data.level = self._level
    return self

  def rule(self, rule: Rule | T_RuleChecker, *rules: Rule | T_RuleChecker) -> Self:
    self._rule &= rule
    for r in rules:
      self._rule &= r
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
    self._brief = brief
    return self

  def usage(self, usage: str | ArgumentParser | Callable[[], str]) -> Self:
    if isinstance(usage, ArgumentParser):
      usage.prog = self.names[0]
      self._usage = usage.format_help()
    else:
      self._usage = usage
    return self

  def category(self, category: str) -> Self:
    self._category = category
    return self

  def shell(self, parser: ArgumentParser, auto_reject: bool = True) -> Self:
    self.rule(ShellCommandRule(self.names[0], parser))
    self._auto_reject = auto_reject
    if not self._usage:
      self.usage(parser)
    return self

  def throttle(self, capacity: int, frequency: float | None = None) -> Self:
    self._capacity = capacity
    self._frequency = frequency
    return self

  def private(self, private: bool) -> Self:
    self.help_data.private = private
    return self

  def help_condition(self, condition: Callable[[help.ShowData], bool]) -> Self:
    self.help_data.condition = condition
    return self

  def state(self, **kw) -> Self:
    self._state.update(kw)
    return self

  def build(self) -> type[Matcher]:
    category = help.CategoryItem.find(self._category, True)
    category.add(help.CommandItem(self.names, self._brief, self._usage, self.help_data))
    _permission = context.build_permission(tuple(self.node.split(".")), self._level)
    matcher = nonebot.on_command(
      self.names[0], self._rule, set(self.names[1:]), permission=_permission, state=self._state,
      _depth=1  # type: ignore
    )
    matcher.__doc__ = self._usage
    if self._capacity:
      add_throttle_handler(matcher, self.names[0], self._capacity, self._frequency)
    if self._auto_reject:
      add_reject_handler(matcher)
    return matcher
