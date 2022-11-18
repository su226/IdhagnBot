import asyncio
import base64
import itertools
import math
import os
import random
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import (
  TYPE_CHECKING, Any, AsyncIterator, Callable, Generator, Iterable, Literal, Sequence, TypeVar
)

import aiohttp
import nonebot
from loguru import logger
from nonebot.adapters.onebot.v11 import Adapter, Bot, Event, Message, MessageEvent, MessageSegment
from nonebot.matcher import matchers
from nonebot.params import Depends
from nonebot.typing import T_State
from pydantic import BaseModel, Field

from .configs import SharedConfig

if TYPE_CHECKING:
  from pyppeteer.browser import Browser


__all__ = [
  "AggregateError", "AnyMessage", "CONFIG", "Config", "Font", "NotCommand", "PromptTimeout",
  "Resample", "ScaleResample", "binomial_sample", "browser", "chunked", "command_start",
  "format_time", "forward_node", "http", "is_command", "local", "prompt", "range_float",
  "range_int", "send_forward_msg", "weighted_choice"
]


T = TypeVar("T")
Resample = Literal["nearest", "bilinear", "bicubic"]
ScaleResample = Resample | Literal["box", "hamming", "lanczos"]
AnyMessage = str | Message | MessageSegment
Quantize = Literal["mediancut", "maxcoverage", "fastoctree"]


class AggregateError(Exception, Sequence[str]):
  def __init__(self, *errors: str | Iterable[str]) -> None:
    super().__init__(*itertools.chain.from_iterable(
      [error] if isinstance(error, str) else error
      for error in errors
    ))

  def __len__(self) -> int:
    return len(self.args)

  def __getitem__(self, index: int) -> str:
    return self.args[index]


class PromptTimeout(asyncio.TimeoutError):
  pass


class Font(BaseModel):
  path: str
  index: int


class Config(BaseModel):
  special_font: dict[str, str] = Field(default_factory=dict)
  font_substitute: dict[str, str] = Field(default_factory=dict)
  chromium: str = ""
  resample: Resample = "bicubic"
  scale_resample: ScaleResample = "bicubic"
  libimagequant: bool = False
  quantize: Quantize = "mediancut"
  dither: bool = True
  backend_local: bool = True


CONFIG = SharedConfig("misc", Config)
ADAPTER_NAME = Adapter.get_name().split(None, 1)[0].lower()
_http: aiohttp.ClientSession | None = None
_driver = nonebot.get_driver()


@asynccontextmanager
async def browser(**options: Any) -> "AsyncIterator[Browser]":
  import pyppeteer
  browser = await pyppeteer.launch(options, executablePath=CONFIG().chromium)
  try:
    yield browser
  finally:
    await browser.close()


def http() -> aiohttp.ClientSession:
  global _http
  if _http is None:
    _http = aiohttp.ClientSession()
  return _http


@_driver.on_shutdown
async def on_shutdown():
  if _http:
    await _http.close()


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


async def prompt(event: MessageEvent, timeout: float | None = 0) -> Message:
  async def check_prompt(event2: MessageEvent):
    return (
      event.user_id == event2.user_id
      and getattr(event, "group_id", -1) == getattr(event2, "group_id", -1)
    )

  async def handle_prompt(event2: MessageEvent):
    future.set_result(event2.get_message())

  if timeout is not None and timeout <= 0:
    timeout = _driver.config.session_expire_timeout.seconds
  future = asyncio.get_event_loop().create_future()
  matcher = nonebot.on_message(check_prompt, handlers=[handle_prompt], priority=-999)
  try:
    result = await asyncio.wait_for(future, timeout)
  except asyncio.TimeoutError as e:
    raise PromptTimeout from e
  finally:
    try:
      matchers[-999].remove(matcher)
    except ValueError:
      pass
  return result


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


def chunked(iterable: Iterable[T], n: int) -> Generator[list[T], None, None]:
  result: list[T] = []
  for i in iterable:
    result.append(i)
    if len(result) == n:
      yield result
      result = []
  if result:
    yield result


def local(type: str, path: str, **kw) -> MessageSegment:
  config = CONFIG()
  if config.backend_local:
    url = "file://" + os.path.abspath(path)
  else:
    with open(path, "rb") as f:
      url = "base64://" + base64.b64encode(f.read()).decode()
  return MessageSegment(type, {"file": url, **kw})


def NotCommand() -> Any:
  def not_command(state: T_State) -> None:
    if "run" in state["_prefix"]:
      logger.warning("util.NotCommand 应该被用于 Rule 而非 Handler 的参数中！")
    state["_as_command"] = False
  return Depends(not_command)


def command_start() -> str:
  for i in _driver.config.command_start:
    return i
  return ""


def is_command(message: Message) -> bool:
  seg = message[0]
  if not seg.is_text():
    return False
  seg = str(seg).lstrip()
  for i in _driver.config.command_start:
    if i and seg.startswith(i):
      return True
  return False


def range_int(min: int | None = None, max: int | None = None) -> Callable[[str], int]:
  info = ""
  if min is not None and max is not None:
    info = f"必须是 {min} 和 {max} 之间的整数"
  elif min is not None:
    info = f"必须是大于等于 {min} 的整数"
  elif max is not None:
    info = f"必须是小于等于 {max} 的整数"

  def func(str_value: str) -> int:
    int_value = int(str_value)
    if min is not None and int_value < min:
      raise ValueError(info)
    if max is not None and int_value > max:
      raise ValueError(info)
    return int_value
  return func


def range_float(
  min: float | None = None, max: float | None = None, inf: bool = False, nan: bool = False
) -> Callable[[str], float]:
  info = ""
  if min is not None and max is not None:
    info = f"必须是 {min} 和 {max} 之间的整数或小数"
  elif min is not None:
    info = f"必须是大于等于 {min} 的整数或小数"
  elif max is not None:
    info = f"必须是小于等于 {max} 的整数或小数"

  def func(str_value: str) -> float:
    float_value = float(str_value)
    if min is not None and float_value < min:
      raise ValueError(info)
    if max is not None and float_value > max:
      raise ValueError(info)
    if not inf and math.isinf(float_value):
      raise ValueError("不能是 inf")
    if not nan and math.isnan(float_value):
      raise ValueError("不能是 nan")
    return float_value
  return func


def binomial_sample(n: int, p: float, random: random.Random = random._inst) -> int:
  # 代码移植至 https://github.com/stdlib-js/random-base-binomial/blob/main/lib/sample2.js
  # 至少不依赖NumPy了（）
  def correction(k: float) -> float:
    k += 1
    v = k ** 2
    return (1 / 12 - ((1 / 360 - (1 / 1260 / v)) / v)) / k

  m = math.floor((n + 1) * p)
  nm = n - m + 1

  q = 1.0 - p

  r = p / q
  nr = (n + 1) * r

  npq = n * p * q
  snpq = math.sqrt(npq)

  b = 1.15 + (2.53 * snpq)
  a = -0.0873 + (0.0248 * b) + (0.01 * p)
  c = (n * p) + 0.5

  alpha = (2.83 + (5.1 / b)) * snpq

  vr = 0.92 - (4.2 / b)
  urvr = 0.86 * vr

  h = (m + 0.5) * math.log((m + 1) / (r * nm))
  h += correction(m) + correction(n - m)

  while True:
    v = random.random()
    if v <= urvr:
      u = (v / vr) - 0.43
      r = (u * ((2.0 * a / (0.5 - abs(u))) + b)) + c
      return math.floor(r)
    if v >= vr:
      u = random.random() - 0.5
    else:
      u = (v / vr) - 0.93
      u = (math.copysign(1, u) * 0.5) - u
      v = vr * random.random()
    us = 0.5 - abs(u)
    k = math.floor((u * ((2.0 * a / us) + b)) + c)
    if k < 0 or k > n:
      continue
    v = v * alpha / ((a / (us * us)) + b)
    km = abs(k - m)
    if km > 15:
      v = math.log(v)
      rho = km / npq
      tmp = ((km / 3) + 0.625) * km
      tmp += 1 / 6
      tmp /= npq
      rho *= tmp + 0.5
      t = -(km * km) / (2.0 * npq)
      if v < t - rho:
        return k
      if v <= t + rho:
        nk = n - k + 1
        x = h + ((n + 1) * math.log(nm / nk))
        x += (k + 0.5) * math.log(nk * r / (k + 1))
        x += -(correction(k) + correction(n - k))
        if v <= x:
          return k
    else:
      f = 1.0
      if m < k:
        for i in range(m, k + 1):
          f *= (nr / i) - r
      elif m > k:
        # JS除以0不会出错，而是Infinity
        if k == 0:
          v = math.inf
        else:
          for i in range(k, m + 1):
            v *= (nr / i) - r
      if v <= f:
        return k


def is_superuser(bot: Bot, user: int) -> bool:
  return f"{ADAPTER_NAME}:{user}" in bot.config.superusers or str(user) in bot.config.superusers


def superusers() -> Generator[int, None, None]:
  driver = nonebot.get_driver()
  for i in driver.config.superusers:
    if i.startswith(ADAPTER_NAME):
      yield int(i[len(ADAPTER_NAME) + 1:])
    else:
      try:
        yield int(i)
      except ValueError:
        pass
