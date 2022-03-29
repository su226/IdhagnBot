from typing import Callable, Any, Generic, NoReturn, TypeVar, Awaitable
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, State
from nonebot.adapters import Bot, Event, Message, MessageSegment, MessageTemplate
from nonebot.typing import T_State as TBotState
import asyncio
import nonebot

class MatchFailed(Exception): pass
class ExcessArguments(MatchFailed): pass
class TooFewArguments(MatchFailed): pass
class InvaildArgument(MatchFailed): pass
class InvaildKeyword(InvaildArgument): pass

TState = TypeVar("TState", bound=dict[str, Any])
TResult = TypeVar("TResult")
class Parser(Generic[TState, TResult]):
  def match(self, args: list[str], state: TState) -> TResult:
    raise NotImplementedError

class Execute(Parser):
  def __init__(self, callback: Callable[..., None]):
    super().__init__()
    self.callback = callback

  def match(self, args: list[str], state: TState) -> TResult:
    if args:
      raise ExcessArguments(f"多余的参数: {args[0]}")
    return self.callback(**state)

class Nextable(Parser):
  _next: list[Parser]

  def __init__(self):
    super().__init__()
    self._next = []

  def feed(self, args: list[str], state: TState) -> list[str]:
    return args

  def match(self, args: list[str], state: TState) -> TResult:
    args = self.feed(args, state)
    if len(self._next) == 1:
      return self._next[0].match(args, state)
    for i in self._next:
      try: return i.match(args, state)
      except MatchFailed: pass
    raise MatchFailed("子命令不存在")

  TParser = TypeVar("TParser", bound=Parser)
  def next(self, next: TParser) -> TParser:
    self._next.append(next)
    return next

class Argument(Nextable):
  def __init__(self, name: str, factory: Callable[[str], Any], count: int | tuple[int, int] = 1):
    super().__init__()
    self.name = name
    self.factory = factory
    self.count = count

  def feed(self, args: list[str], state: TState) -> list[str]:
    if isinstance(self.count, int):
      min_count = max_count = self.count
    else:
      min_count, max_count = self.count
    if len(args) < min_count:
      raise TooFewArguments("参数不足")
    result = []
    for i in args[:min_count]:
      try: result.append(self.factory(i))
      except: raise InvaildArgument("参数无效")
    real_count = min_count
    for i in args[min_count: max_count]:
      try: result.append(self.factory(i))
      except: break
      else: real_count += 1
    state[self.name] = result[0] if min_count == max_count == 1 else result
    return args[real_count:]

class Keyword(Nextable):
  def __init__(self, *keywords: str):
    super().__init__()
    self.keywords = keywords
  
  def feed(self, args: list[str], state: TState) -> list[str]:
    if len(args) < 1:
      raise TooFewArguments("参数不足")
    if args[0] not in self.keywords:
      raise InvaildKeyword("无效关键字")
    return args[1:]

MessageType = str | Message | MessageSegment | MessageTemplate
JudgeFunc = Callable[[Message], Awaitable[TResult | NoReturn]]
PromptFunc = Callable[[JudgeFunc[TResult] | None, MessageType | None], Awaitable[TResult]]

async def _noop_judge(message: Message) -> str:
  return str(message).strip()

class PromptAgain(Exception):
  def __init__(self, message: MessageType = None, **kw):
    self.message = message
    self.kw = kw

class BotCommand(Nextable):
  def __init__(self, matcher: Matcher):
    super().__init__()
    self.matcher = matcher
    matcher.handle()(self._handle)

  async def _handle(self, bot: Bot, event: Event, msg: Message = CommandArg(), state: TBotState = State()):
    async def prompt(judger: JudgeFunc[TResult] = None, initial: MessageType = None, **kw) -> TResult:
      async def check_prompt(event2: Event):
        return event.user_id == event2.user_id and getattr(event, "group_id", -1) == getattr(event2, "group_id", -1)
      async def handle_prompt(event2: Event):
        future.set_result(event2.get_message())
      if judger is None:
        judger = _noop_judge
      if initial:
        await self.matcher.send(initial, **kw)
      while True:
        future = asyncio.get_event_loop().create_future()
        nonebot.on_message(check_prompt, handlers=[handle_prompt], temp=True, priority=-1)
        message = await future
        try:
          return await judger(message)
        except PromptAgain as e:
          if e.message:
            await self.matcher.send(e.message, **e.kw)

    try:
      await self.match(str(msg).split(), {
        "matcher": self.matcher,
        "bot": bot,
        "event": event,
        "prompt": prompt,
      })
    except MatchFailed as e:
      await self.matcher.finish(str(e))
