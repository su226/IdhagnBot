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
  _name: str = PrivateAttr()
  _offset: str = PrivateAttr("-1")


class Config(BaseModel):
  interval: int = 1
  immediate: bool = True
  grpc: bool = True
  concurrency: int = 5
  users: list[User] = Field(default_factory=list)
  ignore_regexs: list[Pattern] = Field(default_factory=list)
  ignore_forward_regexs: list[Pattern] = Field(default_factory=list)
  image_gap: int = 10


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
