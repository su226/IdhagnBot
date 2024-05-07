import asyncio
import time
from io import BytesIO
from typing import List, Optional, Pattern, Union

from PIL import Image, ImageOps
from pydantic import BaseModel, Field, PrivateAttr

from util import configs, misc
from util.api_common.bilibili_activity import GRPC_AVAILABLE


class GroupTarget(BaseModel):
  group: int


class UserTarget(BaseModel):
  user: int


AnyTarget = Union[GroupTarget, UserTarget]


class User(BaseModel):
  uid: int
  targets: List[AnyTarget]
  _name: str = PrivateAttr("未知用户")
  _offset: str = PrivateAttr("-1")
  _time: float = PrivateAttr(default_factory=time.time)


class Config(BaseModel):
  grpc_: bool = Field(True, alias="grpc")
  interval_: Optional[int] = Field(None, alias="interval")
  concurrency_: Optional[int] = Field(None, alias="concurrency")
  users: List[User] = Field(default_factory=list)
  ignore_regexs: List[Pattern[str]] = Field(default_factory=list)
  ignore_forward_regexs: List[Pattern[str]] = Field(default_factory=list)

  @property
  def grpc(self) -> bool:
    return self.grpc_ and GRPC_AVAILABLE

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


CONFIG = configs.SharedConfig("bilibili_activity", Config, "eager")
IMAGE_GAP = 10


class IgnoredException(Exception):
  pass


def check_ignore(forward: bool, content: str):
  config = CONFIG()
  regexs = config.ignore_forward_regexs if forward else config.ignore_regexs
  for regex in regexs:
    if regex.search(content):
      raise IgnoredException(regex)


async def fetch_image(url: str) -> Image.Image:
  async with misc.http().get(url) as response:
    return ImageOps.exif_transpose(Image.open(BytesIO(await response.read())))


async def fetch_images(*urls: str) -> List[Image.Image]:
  return await asyncio.gather(*(fetch_image(url) for url in urls))
