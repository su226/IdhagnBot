import re
from dataclasses import dataclass
from typing import AsyncGenerator
from urllib.parse import quote as encodeuri

from nonebot.adapters.onebot.v11 import MessageSegment

from util import misc

from .base import Music, SearchResult

SEARCH_API = "https://ovooa.com/API/QQ_Music/?msg={keyword}&n={i}"
ID_API = "https://ovooa.com/API/QQ_Music/?id={id}"
ID_RE = re.compile(r"[0-9A-Za-z]{14}")


@dataclass
class QQOvooaMusic(Music):
  keyword: str
  i: int

  async def segment(self) -> MessageSegment:
    http = misc.http()
    async with http.get(SEARCH_API.format(keyword=self.keyword, i=self.i)) as response:
      data = await response.json()
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "qq",
      "url": f"https://y.qq.com/n/ryqq/songDetail/{data['data']['Mid']}",
      "audio": data["data"]["music"],
      "title": self.name,
      "content": self.artists,
      "image": data["data"]["picture"],
    })

  @staticmethod
  async def from_id(id: str) -> MessageSegment:
    if not ID_RE.fullmatch(id):
      raise ValueError("无效ID")
    http = misc.http()
    async with http.get(ID_API.format(id=id)) as response:
      data = await response.json()
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "qq",
      "url": f"https://y.qq.com/n/ryqq/songDetail/{data['data']['Mid']}",
      "audio": data["data"]["music"],
      "title": data["data"]["song"],
      "content": data["data"]["singer"],
      "image": data["data"]["picture"],
    })

  @staticmethod
  async def search(keyword: str, page_size: int) -> SearchResult["QQOvooaMusic"]:
    http = misc.http()
    keyword = encodeuri(keyword)
    async with http.get(SEARCH_API.format(keyword=keyword, i=0)) as response:
      data = await response.json()
    count = len(data["data"])

    async def _musics() -> AsyncGenerator[QQOvooaMusic, None]:
      for i, song in enumerate(data["data"], 1):
        yield QQOvooaMusic(
          song["song"],
          song["singers"],
          "",
          False,
          keyword,
          i
        )

    return SearchResult(count, _musics())
