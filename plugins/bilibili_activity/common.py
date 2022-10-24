import time
from io import BytesIO
from typing import Awaitable, Callable, Pattern, TypeVar

from nonebot.adapters.onebot.v11 import Message
from PIL import Image
from pydantic import BaseModel, Field, PrivateAttr

from util import bilibili_activity, config_v2, util


class GroupTarget(BaseModel):
  group: int


class UserTarget(BaseModel):
  user: int


AnyTarget = GroupTarget | UserTarget


class User(BaseModel):
  uid: int
  targets: list[AnyTarget]
  _name: str = PrivateAttr("未知用户")
  _offset: str = PrivateAttr("-1")
  _time: float = PrivateAttr(default_factory=time.time)


class Config(BaseModel):
  grpc_: bool = Field(True, alias="grpc")
  interval_: int | None = Field(None, alias="interval")
  concurrency_: int | None = Field(None, alias="concurrency")
  users: list[User] = Field(default_factory=list)
  ignore_regexs: list[Pattern] = Field(default_factory=list)
  ignore_forward_regexs: list[Pattern] = Field(default_factory=list)

  @property
  def grpc(self) -> bool:
    return self.grpc_ and bilibili_activity.GRPC_AVAILABLE

  @property
  def interval(self) -> int:
    if self.interval_ is None:
      return 1 if self.grpc else 10
    return self.interval_

  @property
  def concurrency(self) -> int:
    if self.concurrency_ is None:
      return 5 if self.grpc else 1
    return self.concurrency_


CONFIG = config_v2.SharedConfig("bilibili_activity", Config, "eager")
IMAGE_GAP = 10

TContent = TypeVar("TContent", bound=bilibili_activity.Content)
Handler = tuple[TContent, Callable[[bilibili_activity.Activity[TContent]], Awaitable[Message]]]


class IgnoredException(Exception):
  pass


def check_ignore(forward: bool, content: str):
  config = CONFIG()
  regexs = config.ignore_forward_regexs if forward else config.ignore_regexs
  for regex in regexs:
    if regex.search(content):
      raise IgnoredException(regex)


async def fetch_image(url: str) -> Image.Image:
  async with util.http().get(url) as response:
    return Image.open(BytesIO(await response.read()))
