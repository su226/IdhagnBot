import asyncio
import itertools
import random
from contextlib import asynccontextmanager
from datetime import timedelta
from io import BytesIO
from typing import (
  TYPE_CHECKING, Any, AsyncIterator, Generator, Iterable, Literal, Sequence, TypeVar)

import aiohttp
import cairo
import nonebot
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageEvent, MessageSegment
from PIL import Image, ImageChops, ImageDraw, ImageOps
from pydantic import BaseModel, Field

from util.config_v2 import SharedConfig

if TYPE_CHECKING:
  from pyppeteer.browser import Browser

__all__ = [
  "AggregateError", "browser", "cairo_to_pil", "circle", "Config", "CONFIG", "format_time",
  "frames", "get_avatar", "groupbyn", "http", "paste_alpha", "prompt", "resample", "scale_resample",
  "special_font", "weighted_choice", "center", "resize_width", "resize_height", "forward_node",
  "send_forward_msg"]


T = TypeVar("T")
Resample = Literal["nearest", "bilinear", "bicubic"]
ScaleResample = Resample | Literal["box", "hamming", "lanczos"]
AnyMessage = str | Message | MessageSegment


class AggregateError(Exception, Sequence[str]):
  def __init__(self, *errors: str | Iterable[str]) -> None:
    super().__init__(*itertools.chain.from_iterable(
      [error] if isinstance(error, str) else error
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


def center(im: Image.Image, width: int, height: int) -> Image.Image:
  if im.width > width or im.height > height:
    padded_im = ImageOps.pad(im, (width, height), scale_resample)
  else:
    padded_im = Image.new("RGBA", (width, height))
    padded_im.paste(im, ((width - im.width) // 2, (height - im.height) // 2))
  return padded_im


def resize_width(im: Image.Image, width: int) -> Image.Image:
  return ImageOps.contain(im, (width, 99999), scale_resample)


def resize_height(im: Image.Image, height: int) -> Image.Image:
  return ImageOps.contain(im, (99999, height), scale_resample)


def forward_node(id: int, name: str = "", content: AnyMessage = "") -> MessageSegment:
  if not name:
    return MessageSegment("node", {"id": id})
  return MessageSegment("node", {"uin": id, "name": name, "content": content})


async def send_forward_msg(bot: Bot, event: Event, *nodes: MessageSegment | dict) -> Any:
  if gid := getattr(event, "group_id", None):
    return await bot.call_api("send_group_forward_msg", group_id=gid, messages=nodes)
  elif uid := getattr(event, "user_id", None):
    # 需要至少 go-cqhttp 1.0.0-rc2
    return await bot.call_api("send_private_forward_msg", user_id=uid, messages=nodes)
  raise ValueError("event 没有 group_id 和 user_id")


def groupbyn(iterable: Iterable[T], n: int) -> Generator[list[T], None, None]:
  result: list[T] = []
  for i in iterable:
    result.append(i)
    if len(result) == n:
      yield result
      result = []
  if result:
    yield result


async def get_avatar(
  uid: int, *, raw: bool = False, bg: tuple[int, int, int] | bool = False
) -> Image.Image:
  # s 有 100, 160, 640, 1080 分别对应 4 个最大尺寸（可以小）和 0 对应原图（不能不填或者自定义）
  async with http().get(f"https://q1.qlogo.cn/g?b=qq&nk={uid}&s=0") as response:
    raw_avatar = Image.open(BytesIO(await response.read()))
  if raw:
    return raw_avatar
  if bg is False:
    return raw_avatar.convert("RGBA")
  if "A" in raw_avatar.getbands():
    if bg is True:
      bgcolor = (255, 255, 255)
    else:
      bgcolor = bg
    avatar = Image.new("RGB", raw_avatar.size, bgcolor)
    avatar.paste(raw_avatar, mask=raw_avatar.getchannel("A"))  # 也许可能有LA的头像？
    return avatar
  else:
    return raw_avatar.convert("RGB")


def frames(im: Image.Image) -> Generator[Image.Image, None, None]:
  if not getattr(im, "is_animated", False):
    yield im
    return
  for i in range(im.n_frames):
    im.seek(i)
    yield im


def paste_alpha(
  dst: Image.Image, src: Image.Image, box: tuple[int, int], mask: Image.Image | None = None
) -> None:
  if "A" in src.getbands():
    if mask:
      paste_mask = ImageChops.multiply(mask, src.getchannel("A"))
    else:
      paste_mask = src.getchannel("A")
  else:
    paste_mask = mask
  dst.paste(src, box, paste_mask)
