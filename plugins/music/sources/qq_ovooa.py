import re
from dataclasses import dataclass
from typing import AsyncGenerator, Optional
from urllib.parse import quote as encodeuri

from nonebot.adapters.onebot.v11 import MessageSegment

from util import misc

from .base import Music, SearchResult

SEARCH_API = "https://api.f4team.cn/API/QQ_Music_new/?msg={keyword}&limit=50"
ID_API = "https://api.f4team.cn/API/QQ_Music_new/?mid={id}&br={quality}"
ID_RE = re.compile(r"[0-9A-Za-z]{14}")
QUALITY_MASTERTAPE = 14  # 母带
QUALITY_LOSSLESS = 11  # 无损
QUALITY_HIGH = 8  # 高
QUALITY_MEDIUM = 4  # 标准


@dataclass
class QQOvooaMusic(Music):
  mid: str

  @staticmethod
  async def _get_lossless_url(mid: str) -> Optional[str]:
    http = misc.http()
    async with http.get(ID_API.format(id=mid, quality=QUALITY_MASTERTAPE)) as response:
      lossless_data = await response.json()
    return lossless_data["data"]["music"] if lossless_data["data"]["size"]["bit"] is None else None

  async def segment(self) -> MessageSegment:
    http = misc.http()
    async with http.get(ID_API.format(id=self.mid, quality=QUALITY_HIGH)) as response:
      data = await response.json()
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "qq",
      "url": f"https://y.qq.com/n/ryqq/songDetail/{data['data']['mid']}",
      "audio": data["data"]["music"],
      "lossless": await self._get_lossless_url(self.mid),
      "title": self.name,
      "content": self.artists,
      "image": data["data"]["picture"],
    })

  @staticmethod
  async def from_id(id: str) -> MessageSegment:
    if not ID_RE.fullmatch(id):
      raise ValueError("无效ID")
    http = misc.http()
    async with http.get(ID_API.format(id=id, quality=QUALITY_HIGH)) as response:
      data = await response.json()
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "qq",
      "url": f"https://y.qq.com/n/ryqq/songDetail/{data['data']['mid']}",
      "audio": data["data"]["music"],
      "lossless": await QQOvooaMusic._get_lossless_url(id),
      "title": data["data"]["song"],
      "content": data["data"]["singer"],
      "image": data["data"]["picture"],
    })

  @staticmethod
  async def search(keyword: str, page_size: int) -> SearchResult["QQOvooaMusic"]:
    http = misc.http()
    keyword = encodeuri(keyword)
    async with http.get(SEARCH_API.format(keyword=keyword)) as response:
      data = await response.json()
    count = len(data["data"])

    async def _musics() -> AsyncGenerator[QQOvooaMusic, None]:
      for i, song in enumerate(data["data"], 1):
        yield QQOvooaMusic(
          song["song"],
          "/".join(song["singers"]),
          song["album"],
          False,
          song["mid"],
        )

    return SearchResult(count, _musics())
