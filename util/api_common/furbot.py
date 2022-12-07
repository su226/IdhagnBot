import hashlib
import time
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Protocol, Tuple

import nonebot
from aiohttp.client import _RequestContextManager
from nonebot.adapters.onebot.v11 import Bot, Event, MessageEvent, Message
from nonebot.params import EventMessage
from pydantic import BaseModel, SecretStr

from util import configs, context, misc, permission


class Config(BaseModel):
  qq: int = 0
  token: SecretStr = SecretStr("")
  host: str = "https://api.tail.icu"
  keyword: str = "来只毛"
  universal_keyword: str = "来只"
  universal_prefer: Literal["furbot", "foxtail", ""] = ""
CONFIG = configs.SharedConfig("furbot", Config)


def request(api: str, **kw: str) -> _RequestContextManager:
  config = CONFIG()
  http = misc.http()
  t = str(int(time.time()))
  sign = hashlib.md5(f"{api}-{t}-{config.token.get_secret_value()}".encode()).hexdigest()
  params = {
    "qq": str(config.qq),
    "timestamp": t,
    "sign": sign,
    **kw
  }
  return http.get(f"{config.host}/{api}", params=params)


@dataclass
class Picture:
  id: int
  cid: Optional[str]
  name: str
  url: str
  thumb: str


class FurbotException(Exception):
  def __init__(self, code: int, message: str) -> None:
    super().__init__(code, message)
    self.code = code
    self.message = message


async def get_daily_by_id(id: int) -> Picture:
  async with request("api/v2/DailyFursuit/id", id=str(id)) as response:
    data = await response.json()
  if (code := data["code"]) != 200:
    raise FurbotException(code, data["msg"])
  return Picture(
    data["data"]["id"],
    None,
    data["data"]["name"],
    data["data"]["url"],
    data["data"]["thumb"],
  )


async def get_daily_by_name(name: str) -> Picture:
  async with request("api/v2/DailyFursuit/name", name=name) as response:
    data = await response.json()
  if (code := data["code"]) != 200:
    raise FurbotException(code, data["msg"])
  return Picture(
    data["data"]["id"],
    None,
    data["data"]["name"],
    data["data"]["url"],
    data["data"]["thumb"],
  )


async def get_daily_random() -> Picture:
  async with request("api/v2/DailyFursuit/Rand") as response:
    data = await response.json()
  if (code := data["code"]) != 200:
    raise FurbotException(code, data["msg"])
  return Picture(
    data["data"]["id"],
    None,
    data["data"]["name"],
    data["data"]["url"],
    data["data"]["thumb"],
  )


async def get_random() -> Picture:
  async with request("api/v2/getFursuitRand") as response:
    data = await response.json()
  if (code := data["code"]) != 200:
    raise FurbotException(code, data["msg"])
  return Picture(
    data["data"]["id"],
    data["data"]["cid"],
    data["data"]["name"],
    data["data"]["url"],
    data["data"]["thumb"],
  )


async def get_by_name(name: str) -> Picture:
  async with request("api/v2/getFursuitByName", name=name) as response:
    data = await response.json()
  if (code := data["code"]) != 200:
    raise FurbotException(code, data["msg"])
  return Picture(
    data["data"]["id"],
    data["data"]["cid"],
    data["data"]["name"],
    data["data"]["url"],
    data["data"]["thumb"],
  )


async def get_by_id(id: int) -> Picture:
  async with request("api/v2/getFursuitByID", fid=str(id)) as response:
    data = await response.json()
  if (code := data["code"]) != 200:
    raise FurbotException(code, data["msg"])
  return Picture(
    data["data"]["id"],
    data["data"]["cid"],
    data["data"]["name"],
    data["data"]["url"],
    data["data"]["thumb"],
  )


async def query_id(name: str) -> Tuple[str, List[int]]:
  async with request("api/v2/getFursuitFid", name=name) as response:
    data = await response.json()
  if (code := data["code"]) != 200:
    raise FurbotException(code, data["msg"])
  return data["data"]["name"], data["data"]["fids"]


class Source(Protocol):
  name: str
  node: Tuple[str, ...]
  @staticmethod
  def keyword() -> str: ...
  @staticmethod
  def available() -> bool: ...
  @staticmethod
  async def handle(bot: Bot, event: Event, args: str) -> None: ...


universal_keyword_registered = False
universal_sources: Dict[str, Source] = {}


async def check_universal_keyword(msg: Message = EventMessage()) -> bool:
  config = CONFIG()
  if not config.universal_keyword:
    return False
  seg = msg[0]
  return seg.is_text() and str(seg).lstrip().startswith(config.universal_keyword)


def available(source: Source, event: MessageEvent, event_level: permission.Level) -> bool:
  if not source.available():
    return False
  group_id = context.get_event_context(event)
  if permission.check(source.node, event.user_id, group_id, event_level) is False:
    return False
  command_level = permission.get_node_level(source.node) or permission.Level.MEMBER
  return event_level >= command_level


async def handle_universal_keyword(
  bot: Bot, event: MessageEvent, msg: Message = EventMessage()
) -> None:
  config = CONFIG()
  args = misc.removeprefix(msg.extract_plain_text().lstrip(), config.universal_keyword).strip()
  source = universal_sources.get(config.universal_prefer, None)
  event_level = await context.get_event_level(bot, event)
  if source is None or not available(source, event, event_level):
    sources = [x for x in universal_sources.values() if available(x, event, event_level)]
    if len(sources) > 1:
      message = "\n".join(f"如需使用{x.name}，请发送“{x.keyword()} {args}”" for x in sources)
      await bot.send(event, message)
      return
    elif not sources:
      await bot.send(event, "似乎没有可用的兽图来源")
      return
    source = sources[0]
  await source.handle(bot, event, args)


def register_universal_keyword() -> None:
  global universal_keyword_registered
  if not universal_keyword_registered:
    matcher = nonebot.on_message(
      check_universal_keyword,
      context.build_permission(("furbot", "universal_keyword"), permission.Level.MEMBER),
      priority=2
    )
    matcher.handle()(handle_universal_keyword)
    universal_keyword_registered = True
