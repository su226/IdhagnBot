import asyncio
import shlex
from collections import deque
from typing import (
  Any, Callable, Deque, Dict, List, Literal, NoReturn, Optional, Tuple, Type, Union, cast
)

import nonebot
from apscheduler.job import Job
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import Message
from nonebot.consts import PREFIX_KEY, RAW_CMD_KEY, SHELL_ARGS, SHELL_ARGV
from nonebot.exception import ParserExit
from nonebot.matcher import Matcher, current_matcher
from nonebot.params import CommandArg, ShellCommandArgs
from nonebot.rule import TRIE_VALUE, ArgumentParser, CommandRule, Rule, TrieRule, parser_message
from nonebot.typing import T_RuleChecker, T_State
from typing_extensions import Self

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from . import context, help, permission

IDHAGNBOT_KEY = "_idhagnbot"
USAGE_KEY = "usage"
driver = nonebot.get_driver()


class ShellCommandRule:
  # 修改自 nonebot.rule.ShellCommandRule
  # 特殊处理不是纯文本的消息段，以及 shlex 抛出 ValueError 的情况
  __slots__ = "parser"

  def __init__(self, parser: ArgumentParser):
    self.parser = parser

  async def __call__(self, state: T_State, msg: Optional[Message] = CommandArg()) -> bool:
    if msg is None:  # 去掉 None 虽然不影响功能，但 DEBUG 日志等级下会刷屏
      return False
    try:
      argv = self.split(msg)
      state[SHELL_ARGV] = argv
    except ValueError as e:
      state[SHELL_ARGV] = []
      state[SHELL_ARGS] = ParserExit(2, "解析命令行参数失败：" + str(e))
      return True
    token = parser_message.set("")
    try:
      args = self.parser.parse_args(argv)
      state[SHELL_ARGS] = args
    except ParserExit as e:
      state[SHELL_ARGS] = e
    parser_message.reset(token)
    return True

  @staticmethod
  def split(msg: Message) -> List[str]:
    args: List[str] = []
    for seg in msg:
      if seg.is_text():
        args.extend(shlex.split(str(seg)))
      else:
        args.append(str(seg))
    return args


def add_reject_handler(matcher: Type[Matcher]) -> None:
  async def handler(state: T_State, args: ParserExit = ShellCommandArgs()) -> None:
    message = None
    if args.message:
      message = args.message.rstrip().replace("__cmd__", state[PREFIX_KEY][RAW_CMD_KEY])
    await matcher.finish(message)
  matcher.handle()(handler)


class TokenBucket:
  def __init__(self, capacity: int, frequency: Optional[float]) -> None:
    self.capacity = capacity
    self.frequency = 1 / capacity if frequency is None else frequency
    self.tokens = capacity
    self.queue: Deque[asyncio.Future[None]] = deque()
    self.job: Optional[Job] = None

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
  matcher: Type[Matcher], capacity: int, frequency: Optional[float]
) -> None:
  async def handle_throttle(state: T_State):
    estimated = token.estimate()
    command = state[PREFIX_KEY][RAW_CMD_KEY]
    if estimated >= 60:
      await matcher.finish(f"当前使用 {command} 的人数过多，请稍后再试。")
    if estimated >= 10:
      await matcher.send(f"当前使用 {command} 的人数较多，请等待大约 {int(estimated)} 秒。")
    await token.acquire()

  token = TokenBucket(capacity, frequency)
  matcher.handle()(handle_throttle)


async def finish_with_usage() -> NoReturn:
  matcher = current_matcher.get()
  usage = cast(Union[str, Callable[[], str]], matcher.state[IDHAGNBOT_KEY][USAGE_KEY])
  if isinstance(usage, Callable):
    usage = usage()
  await matcher.finish(usage.replace("__cmd__", matcher.state[PREFIX_KEY][RAW_CMD_KEY]))


class SerialRule:
  def __init__(self, *rules: Union[Rule, T_RuleChecker]) -> None:
    self.rules = [rule if isinstance(rule, Rule) else Rule(rule) for rule in rules]

  async def __call__(self, bot: Bot, event: Event, state: T_State) -> bool:
    for rule in self.rules:
      if not await rule(
        bot,
        event,
        state,
        context._current_stack.get(),
        context._current_dependency_cache.get(),
      ):
        return False
    return True


class CommandBuilder:
  def __init__(self, node: str, name: str, *names: str) -> None:
    self.node = node
    self.names = [name, *names]
    self._rule = Rule()
    self._level = permission.Level.MEMBER
    self._auto_reject = False
    self._state: Dict[str, Any] = {}

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

  def rule(self, rule: Union[Rule, T_RuleChecker], *rules: Union[Rule, T_RuleChecker]) -> Self:
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

  def usage(self, usage: Union[str, ArgumentParser, Callable[[], str]]) -> Self:
    if isinstance(usage, ArgumentParser):
      usage.prog = "__cmd__"
      self._usage = usage.format_help().rstrip()
    else:
      self._usage = usage
    return self

  def category(self, category: str) -> Self:
    self._category = category
    return self

  def shell(self, parser: ArgumentParser, auto_reject: bool = True) -> Self:
    self.rule(ShellCommandRule(parser))
    self._auto_reject = auto_reject
    if not self._usage:
      self.usage(parser)
    return self

  def throttle(self, capacity: int, frequency: Optional[float] = None) -> Self:
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

  def build(self) -> Type[Matcher]:
    category = help.CategoryItem.find(self._category, True)
    category.add(help.CommandItem(self.names, self._brief, self._usage, self.help_data))
    permission = context.build_permission(tuple(self.node.split(".")), self._level)
    self._state.update({
      IDHAGNBOT_KEY: {
        USAGE_KEY: self._usage
      }
    })
    command_start = nonebot.get_driver().config.command_start
    commands: List[Tuple[str, ...]] = []
    for command in self.names:
      command = (command,)
      commands.append(command)
      for start in command_start:
        TrieRule.add_prefix(f"{start}{command[0]}", TRIE_VALUE(start, command))
    matcher = nonebot.on_message(
      SerialRule(CommandRule(commands), self._rule), permission, state=self._state, block=False,
      _depth=1  # type: ignore
    )
    if isinstance(self._usage, str):  # 已弃用，使用 finish_with_usage
      matcher.__doc__ = self._usage.replace("__cmd__", self.names[0])
    if self._capacity:
      add_throttle_handler(matcher, self._capacity, self._frequency)
    if self._auto_reject:
      add_reject_handler(matcher)
    return matcher
