from dataclasses import dataclass
from typing import AsyncGenerator, Generic, TypeVar

from nonebot.adapters.onebot.v11 import MessageSegment

T = TypeVar("T", bound="Music", covariant=True)
@dataclass
class SearchResult(Generic[T]):
  count: int
  musics: AsyncGenerator[T, None]


@dataclass
class Music:
  name: str
  artists: str
  album: str
  vip: bool

  async def segment(self) -> MessageSegment:
    raise NotImplementedError

  @staticmethod
  async def from_id(id: str) -> MessageSegment:
    raise ValueError("该来源不支持从ID获取")

  @staticmethod
  async def search(keyword: str, page_size: int) -> SearchResult["Music"]:
    raise NotImplementedError
