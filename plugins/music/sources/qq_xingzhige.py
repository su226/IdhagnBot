import re
from dataclasses import dataclass
from typing import AsyncGenerator, Optional
from urllib.parse import quote as encodeuri

from nonebot.adapters.onebot.v11 import MessageSegment

from util import misc

from .base import Music, SearchResult

SEARCH_API = "https://api.xingzhige.com/API/QQmusicVIP/?name={keyword}&max=60"
ID_API = "https://api.xingzhige.com/API/QQmusicVIP/?mid={id}&br={quality}"
ID_RE = re.compile(r"[0-9A-Za-z]{14}")
QUALITY_MASTERTAPE = 14  # 母带
QUALITY_LOSSLESS = 11  # 无损
QUALITY_HIGH = 8  # 高(320k)
QUALITY_MEDIUM = 4  # 标准(128k)


@dataclass
class QQXinzhigeMusic(Music):
  mid: str

  @staticmethod
  async def _get_lossless_url(mid: str) -> Optional[str]:
    http = misc.http()
    async with http.get(ID_API.format(id=mid, quality=QUALITY_MASTERTAPE)) as response:
      lossless_data = await response.json()
    kbps = int(misc.removesuffix(lossless_data["data"]["kbps"], "kbps"))
    return lossless_data["data"]["src"] if kbps > 320 else None

  async def segment(self) -> MessageSegment:
    http = misc.http()
    async with http.get(ID_API.format(id=self.mid, quality=QUALITY_HIGH)) as response:
      data = await response.json()
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "qq",
      "url": f"https://y.qq.com/n/ryqq/songDetail/{data['data']['mid']}",
      "audio": data["data"]["src"],
      "lossless": await self._get_lossless_url(self.mid),
      "title": self.name,
      "content": self.artists,
      "image": data["data"]["cover"],
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
      "audio": data["data"]["src"],
      "lossless": await QQXinzhigeMusic._get_lossless_url(id),
      "title": data["data"]["songname"],
      "content": data["data"]["name"],
      "image": data["data"]["cover"],
    })

  @staticmethod
  async def search(keyword: str, page_size: int) -> SearchResult["QQXinzhigeMusic"]:
    http = misc.http()
    keyword = encodeuri(keyword)
    async with http.get(SEARCH_API.format(keyword=keyword)) as response:
      data = await response.json()
    songs = data.get("data", [])

    async def _musics() -> AsyncGenerator[QQXinzhigeMusic, None]:
      for song in songs:
        yield QQXinzhigeMusic(
          song["songname"],
          song["name"],
          song["album"],
          False,
          song["mid"],
        )

    return SearchResult(len(songs), _musics())
