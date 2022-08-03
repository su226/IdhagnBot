import asyncio
import itertools
import random
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import TYPE_CHECKING, Any, AsyncIterator, Literal, Sequence, TypeVar

import aiohttp
import cairo
import nonebot
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from PIL import Image, ImageChops, ImageDraw
from pydantic import BaseModel, Field

from util.config_v2 import SharedConfig

if TYPE_CHECKING:
  from pyppeteer.browser import Browser

__all__ = [
  "AggregateError", "browser", "Config", "CONFIG", "format_time", "http", "prompt", "resample",
  "scale_resample", "special_font", "weighted_choice"]


T = TypeVar("T")
Resample = Literal["nearest", "bilinear", "bicubic"]
ScaleResample = Resample | Literal["box", "hamming", "lanczos"]


class AggregateError(Exception, Sequence[str]):
  def __init__(self, *errors: "str | AggregateError") -> None:
    super().__init__(*itertools.chain.from_iterable(
      error if isinstance(error, AggregateError) else [error]
      for error in errors))

  def __len__(self) -> int:
    return len(self.args)

  def __getitem__(self, index: int) -> str:
    return self.args[index]


class Font(BaseModel):
  path: str
  index: int


class Config(BaseModel):
  special_font: dict[str, str] = Field(default_factory=dict)
  font_substitute: dict[str, str] = Field(default_factory=dict)
  chromium: str = ""
  resample: Resample = "bicubic"
  scale_resample: ScaleResample = "bicubic"


CONFIG = SharedConfig("util", Config)
resample = Image.Resampling.BICUBIC
scale_resample = Image.Resampling.BICUBIC
http_session: aiohttp.ClientSession | None = None


@CONFIG.onload()
def config_onload(old: Config | None, cur: Config) -> None:
  global resample, scale_resample
  resample = Image.Resampling[cur.resample.upper()]
  scale_resample = Image.Resampling[cur.scale_resample.upper()]


def special_font(name: str, fallback: str) -> str:
  if value := CONFIG().special_font.get(name, None):
    return value
  return fallback


@asynccontextmanager
async def browser(**options: Any) -> "AsyncIterator[Browser]":
  import pyppeteer
  browser = await pyppeteer.launch(options, executablePath=CONFIG().chromium)
  try:
    yield browser
  finally:
    await browser.close()


def http() -> aiohttp.ClientSession:
  global http_session
  if http_session is None:
    http_session = aiohttp.ClientSession()
  return http_session


def weighted_choice(choices: list[T | tuple[T, float]]) -> T:
  raw_choices = []
  weights = []
  for i in choices:
    if isinstance(i, tuple):
      raw_choices.append(i[0])
      weights.append(i[1])
    else:
      raw_choices.append(i)
      weights.append(1)
  return random.choices(raw_choices, weights)[0]


def format_time(seconds: float | timedelta) -> str:
  if isinstance(seconds, timedelta):
    seconds = seconds.seconds
  seconds = round(seconds)
  minutes, seconds = divmod(seconds, 60)
  hours, minutes = divmod(minutes, 60)
  days, hours = divmod(hours, 24)
  segments = []
  if days:
    segments.append(f"{days} 天")
  if hours:
    segments.append(f"{hours} 时")
  if minutes:
    segments.append(f"{minutes} 分")
  if seconds:
    segments.append(f"{seconds} 秒")
  return " ".join(segments)


def prompt(event: MessageEvent) -> asyncio.Future[Message]:
  async def check_prompt(event2: MessageEvent):
    return (
      event.user_id == event2.user_id
      and getattr(event, "group_id", -1) == getattr(event2, "group_id", -1))

  async def handle_prompt(event2: MessageEvent):
    future.set_result(event2.get_message())

  future = asyncio.get_event_loop().create_future()
  nonebot.on_message(check_prompt, handlers=[handle_prompt], temp=True, priority=-1)
  return future


def circle(im: Image.Image, antialias: bool = True):
  if antialias:
    mask = Image.new("L", (im.width * 2, im.height * 2))
  else:
    mask = Image.new("L", im.size)
  draw = ImageDraw.Draw(mask)
  draw.ellipse((0, 0, mask.width - 1, mask.height - 1), 255)
  if antialias:
    mask = mask.resize(im.size, scale_resample)
  if "A" in im.getbands():
    mask = ImageChops.multiply(im.getchannel("A"), mask)
  im.putalpha(mask)


def cairo_to_pil(surface: cairo.ImageSurface) -> Image.Image:
  w = surface.get_width()
  h = surface.get_height()
  data = surface.get_data()
  if not data:  # 大小为0，data为None
    return Image.new("RGBA", (w, h))
  b, g, r, a = Image.frombytes("RGBa", (w, h), bytes(data)).convert("RGBA").split()
  return Image.merge("RGBA", (r, g, b, a))  # BGRa -> BGRA -> RGBA
