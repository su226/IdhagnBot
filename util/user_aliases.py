import asyncio
import itertools
import re
import time
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from types import TracebackType
from typing import (
  Any, Awaitable, Coroutine, Dict, List, Literal, Optional, Sequence, Tuple, Type, TypeVar, Union,
  overload,
)

import aiohttp
from nonebot.adapters.onebot.v11 import ActionFailed, Bot, Event, Message, MessageEvent
from nonebot.exception import FinishedException
from PIL import Image
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from typing_extensions import Self

from util import configs, context, imutil, misc, user_aliases
from util.misc import AggregateError


class Alias(BaseModel):
  names: List[str]
  users: Tuple[int, ...]


class Aliases(BaseModel):
  contexts: List[int] = Field(default_factory=list)
  aliases: List[Alias]


class Config(BaseModel):
  aliases: List[Aliases] = Field(default_factory=list)


@dataclass
class MatchPattern:
  name: str
  exact: bool

  def __str__(self) -> str:
    return f"*{self.name}" if self.exact else self.name


@dataclass
class Match:
  uids: Sequence[int]
  patterns: List[MatchPattern]

  def __str__(self) -> str:
    if len(self.uids) > 1:
      return f"{self.uids[0]} 等 {len(self.uids)} 个成员"
    return str(self.uids[0])


AliasesDict = Dict[int, Alias]
T = TypeVar("T")

CONFIG = configs.SharedConfig("user_aliases", Config)
CACHE: Dict[int, Tuple[float, AliasesDict]] = {}
IDENTIFIER_RE = re.compile(r"[a-zA-Z0-9\u4e00-\u9fa5]+")
AMBIGUOUS_LIMIT = 5
AT_RE = re.compile(r"^\[CQ:at,qq=(\d+|all)(?:,[^\]]+)?\]$")
LINK_RE = re.compile(r"^https?://.+$")
IMAGE_RE = re.compile(r"^\[CQ:image[^\]]+\]$")


@CONFIG.onload()
def onload(prev: Optional[Config], curr: Config) -> None:
  CACHE.clear()


def to_identifier(data: Optional[str]) -> str:
  if not data:
    return ""
  return "".join(IDENTIFIER_RE.findall(data)).lower()


async def get_aliases(bot: Bot, event: Event) -> AliasesDict:
  config = CONFIG()
  ctx = context.get_event_context(event)
  curtime = time.time()
  cachetime, aliases = CACHE.get(ctx, (0.0, {}))
  if cachetime > curtime - 600:
    return aliases
  aliases: AliasesDict = {}
  CACHE[ctx] = (curtime, aliases)
  for i in config.aliases:
    if not context.in_group(ctx, *i.contexts):
      continue
    for alias in i.aliases:
      key = hash(alias.users)
      if key not in aliases:
        aliases[key] = Alias(names=[], users=alias.users)
      aliases[key].names.extend(alias.names)
  if ctx == context.PRIVATE:
    return aliases
  for user in await bot.call_api("get_group_member_list", group_id=ctx, no_cache=True):
    users = (user["user_id"],)
    key = hash(users)
    if key not in aliases:
      aliases[key] = Alias(names=[], users=users)
    aliases[key].names.extend(filter(len, {
      to_identifier(user["nickname"]),
      to_identifier(user["card"]),
    }))
  return aliases


async def match(bot: Bot, event: Event, pattern: str) -> Tuple[Dict[int, Match], Dict[int, Match]]:
  def get(matches: Dict[int, Match], id: int, alias: Alias) -> Match:
    if id not in matches:
      matches[id] = Match(alias.users, [])
    return matches[id]
  exact: Dict[int, Match] = {}
  inexact: Dict[int, Match] = {}
  for id, alias in (await get_aliases(bot, event)).items():
    for name in alias.names:
      if pattern == name:
        matched = MatchPattern(name, True)
        get(exact, id, alias).patterns.append(matched)
      elif pattern in name:
        matched = MatchPattern(name, False)
        if id in exact:
          exact[id].patterns.append(matched)
        else:
          get(inexact, id, alias).patterns.append(matched)
  return exact, inexact


@overload
async def match_uid(
  bot: Bot, event: Event, raw_pattern: str, multiple: Literal[False] = ...,
) -> int: ...
@overload
async def match_uid(
  bot: Bot, event: Event, raw_pattern: str, multiple: Literal[True] = ...,
) -> Sequence[int]: ...
async def match_uid(
  bot: Bot, event: Event, raw_pattern: str, multiple: bool = False,
) -> Union[int, Sequence[int]]:
  try:
    uid = int(raw_pattern)
    if multiple:
      return (uid,)
    return uid
  except ValueError:
    pass
  pattern = to_identifier(raw_pattern)
  if not pattern:
    raise AggregateError(f"有效名字为空：{raw_pattern}")
  exact, inexact = await match(bot, event, pattern)
  matches = list((exact or inexact).values())
  if len(matches) > 1:
    count = len(exact) + len(inexact)
    segments = [f"{pattern} 具有歧义，可以指："]
    values = itertools.chain(exact.values(), inexact.values())
    for _, i in zip(range(AMBIGUOUS_LIMIT), values):
      segments.append(f"{i}（{'、'.join(map(str, i.patterns))}）")
    if count > AMBIGUOUS_LIMIT:
      segments.append(f"等 {count} 个成员或别名")
    raise AggregateError("\n".join(segments))
  elif len(matches) == 0:
    if pattern == raw_pattern:
      display_pattern = pattern
    else:
      display_pattern = f"{raw_pattern}（{pattern}）"
    raise AggregateError(f"找不到 {display_pattern}")
  if not multiple and len(matches[0].uids) > 1:
    comment = " "
    if len(matches[0].patterns) > 1:
      comment = "（" + "、".join(map(str, matches[0].patterns[1:])) + "）"
    raise AggregateError(f"{matches[0].patterns[0]}{comment}包含多个成员")
  if multiple:
    return matches[0].uids
  return matches[0].uids[0]


async def download_image(
  url: str, *, crop: bool = True, raw: bool = False, bg: Union[Tuple[int, int, int], bool] = False,
) -> Image.Image:
  async with misc.http().get(url) as response:
    data = await response.read()

  def process() -> Image.Image:
    image = Image.open(BytesIO(data))
    if raw:
      return image
    if crop:
      image = imutil.square(image)
    if bg is False:
      return image.convert("RGBA")
    return imutil.background(image, (255, 255, 255) if bg is True else bg)
  return await misc.to_thread(process)


async def get_image_from_link(url: str, **kw: Any) -> Image.Image:
  try:
    return await asyncio.wait_for(download_image(url, **kw), 10)
  except asyncio.TimeoutError as e:
    raise misc.AggregateError(f"下载图片超时：{url}") from e
  except aiohttp.ClientError as e:
    raise misc.AggregateError(f"下载图片失败：{url}") from e
  except Exception as e:
    raise misc.AggregateError(f"无效图片：{url}") from e


async def get_avatar(uid: int, *, crop: bool = True, **kw: Any) -> Image.Image:
  try:
    return await asyncio.wait_for(imutil.get_avatar(uid, **kw), 10)
  except asyncio.TimeoutError:
    # 以防有笨b（其实是我自己）眼瞎，这里的错误信息和上面的不一样
    raise misc.AggregateError(f"下载头像超时：{uid}")
  except aiohttp.ClientError:
    raise misc.AggregateError(f"下载头像失败：{uid}")


class DefaultType(Enum):
  TARGET = "TARGET"
  SOURCE = "SOURCE"


async def _get_image_and_user(
  bot: Bot, event: MessageEvent, pattern: str, default: DefaultType, **kw: Any,
) -> Tuple[Image.Image, Optional[int]]:
  if pattern in {"?", "那个", "它"}:
    if not event.reply:
      raise misc.AggregateError("它是什么？你得回复一张图片")
    url = ""
    for seg in event.reply.message:
      if seg.type == "image":
        if url:
          raise misc.AggregateError("回复的消息有不止一张图片")
        url = seg.data["url"]
    if not url:
      raise misc.AggregateError("回复的消息没有图片")
    return await download_image(url, **kw), None
  if not pattern:
    if default == DefaultType.TARGET:
      if event.reply:
        try:
          reply_msg = await bot.get_msg(message_id=event.reply.message_id)
          reply_sender = reply_msg["sender"]["user_id"]
          for seg in TypeAdapter(Message).validate_python(reply_msg["message"]):
            if seg.type == "image":
              return await get_image_from_link(seg.data["url"], **kw), None
        except (ActionFailed, ValidationError):
          reply_sender = event.reply.sender.user_id
        uid = reply_sender or event.self_id
      else:
        uid = event.self_id
    else:
      uid = event.user_id
  elif match := AT_RE.match(pattern):
    if match[1] == "all":
      raise misc.AggregateError("不支持@全体成员，恭喜你浪费了一次")
    uid = int(match[1])
  elif IMAGE_RE.match(pattern):
    return await get_image_from_link(Message(pattern)[0].data["url"], **kw), None
  elif match := LINK_RE.match(pattern):
    return await get_image_from_link(pattern, **kw), None
  elif pattern in {"~", "自己", "我"}:
    uid = event.user_id
  elif pattern.lower() in {"0", "机器人", "bot", "你"}:
    uid = event.self_id
  elif pattern in {"!", "他", "她", "牠", "祂"}:
    if not event.reply:
      raise misc.AggregateError("他是谁？你得回复一个人")
    uid = event.reply.sender.user_id
    if not uid:
      raise misc.AggregateError("他是谁？你得回复一个人")
  else:
    uid = await user_aliases.match_uid(bot, event, pattern)
  return await get_avatar(uid, **kw), uid


class _Prompter:
  def __init__(self, bot: Bot, event: MessageEvent, prompt: str) -> None:
    self.bot = bot
    self.event = event
    self.message = "这个是什么？请发送一张图片"
    if prompt:
      self.message += f"作为{prompt}"
    self.prev_future: Optional[asyncio.Future[None]] = None
    self.next_future: Optional[asyncio.Future[None]] = None

  async def __call__(self) -> str:
    if self.prev_future:
      await self.prev_future
    await self.bot.send(self.event, self.message)
    try:
      message = await misc.prompt(self.event)
    except misc.PromptTimeout as e:
      raise misc.AggregateError("等待回应超时") from e
    url = ""
    for seg in message:
      if seg.type == "image":
        if url:
          raise misc.AggregateError("发送的消息有不止一张图片")
        url = seg.data["url"]
    if not url:
      raise misc.AggregateError("发送的消息没有图片")
    if self.next_future and not self.next_future.cancelled():
      self.next_future.set_result(None)
    return url


async def _get_from_prompter(task: "asyncio.Task[str]", **kw: Any) -> Tuple[Image.Image, None]:
  return await download_image(await task, **kw), None


class AvatarGetter:
  def __init__(self, bot: Bot, event: MessageEvent) -> None:
    self.bot = bot
    self.event = event
    self.tasks: List[asyncio.Task[Any]] = []
    self.prompter_tasks: List[asyncio.Task[str]] = []
    self.last_prompter: Optional[_Prompter] = None

  def get(
    self, pattern: str, default: DefaultType, prompt: str = "",
    crop: bool = True, raw: bool = False, bg: Union[Tuple[int, int, int], bool] = False,
  ) -> Coroutine[Any, Any, Tuple[Image.Image, Optional[int]]]:
    if pattern in {"-", "这个"}:
      prompter = _Prompter(self.bot, self.event, prompt)
      if self.last_prompter:
        future = asyncio.get_running_loop().create_future()
        self.last_prompter.next_future = prompter.prev_future = future
      self.last_prompter = prompter
      prompter_task = asyncio.create_task(prompter())
      self.prompter_tasks.append(prompter_task)
      return _get_from_prompter(prompter_task, crop=crop, raw=raw, bg=bg)
    return _get_image_and_user(self.bot, self.event, pattern, default, crop=crop, raw=raw, bg=bg)

  def submit(self, coro: Awaitable[T], /) -> "asyncio.Task[T]":
    task = asyncio.ensure_future(coro)
    self.tasks.append(task)
    return task

  def __call__(
    self, pattern: str, default: DefaultType, prompt: str = "",
    crop: bool = True, raw: bool = False, bg: Union[Tuple[int, int, int], bool] = False,
  ) -> "asyncio.Task[Tuple[Image.Image, Optional[int]]]":
    return self.submit(self.get(pattern, default, prompt, crop, raw, bg))

  async def __aenter__(self) -> Self:
    return self

  async def __aexit__(
    self, exc_type: Type[BaseException], exc: BaseException, tb: TracebackType,
  ) -> None:
    errors: List[str] = []
    for i in asyncio.as_completed(self.tasks):
      try:
        await i
      except misc.AggregateError as e:
        for prompter_task in self.prompter_tasks:
          prompter_task.cancel()
        errors.extend(e)
      except asyncio.CancelledError:
        pass
    if errors:
      await self.bot.send(self.event, "\n".join(errors))
      raise FinishedException
