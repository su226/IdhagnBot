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

  def segment(self) -> MessageSegment:
    raise NotImplementedError

  @staticmethod
  async def search(keyword: str) -> SearchResult["Music"]:
    raise NotImplementedError
