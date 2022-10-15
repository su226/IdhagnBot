import hashlib
import time
from dataclasses import dataclass
from typing import Protocol

import nonebot
from aiohttp.client import _RequestContextManager
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import EventMessage
from pydantic import BaseModel

from util import config_v2, util


class Config(BaseModel):
  qq: int = 0
  token: str = ""
  host: str = "https://api.tail.icu"
  keyword: str = "来只毛"
  universal_keyword: str = "来只"
CONFIG = config_v2.SharedConfig("furbot", Config)


def request(api: str, **kw: str) -> _RequestContextManager:
  config = CONFIG()
  http = util.http()
  t = str(int(time.time()))
  sign = hashlib.md5(f"{api}-{t}-{config.token}".encode()).hexdigest()
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
  cid: str | None
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


async def query_id(name: str) -> tuple[str, list[int]]:
  async with request("api/v2/getFursuitFid", name=name) as response:
    data = await response.json()
  if (code := data["code"]) != 200:
    raise FurbotException(code, data["msg"])
  return data["data"]["name"], data["data"]["fids"]


class Source(Protocol):
  @staticmethod
  def name() -> str: ...
  @staticmethod
  def keyword() -> str: ...
  @staticmethod
  def available() -> bool: ...
  @staticmethod
  async def handle(bot: Bot, event: Event, args: str) -> None: ...


universal_keyword_registered = False
universal_sources: list[Source] = []


async def check_universal_keyword(msg: Message = EventMessage()) -> bool:
  config = CONFIG()
  if not config.universal_keyword:
    return False
  seg = msg[0]
  return seg.is_text() and str(seg).lstrip().startswith(config.universal_keyword)


async def handle_universal_keyword(bot: Bot, event: Event, msg: Message = EventMessage()) -> None:
  config = CONFIG()
  args = msg.extract_plain_text().lstrip().removeprefix(config.universal_keyword).strip()
  sources = [x for x in universal_sources if x.available()]
  if len(sources) > 1:
    message = "\n".join(f"如需使用{x.name()}，请发送“{x.keyword()} {args}”" for x in sources)
    await bot.send(event, message)
    return
  await sources[0].handle(bot, event, args)


def register_universal_keyword() -> None:
  global universal_keyword_registered
  if not universal_keyword_registered:
    matcher = nonebot.on_message(check_universal_keyword, priority=2)
    matcher.handle()(handle_universal_keyword)
    universal_keyword_registered = True
