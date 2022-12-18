from dataclasses import dataclass
from typing import AsyncGenerator
from urllib.parse import quote as encodeuri

from nonebot.adapters.onebot.v11 import MessageSegment

from util import misc

from .base import Music, SearchResult

SEARCH_API = (
  "https://api.bilibili.com/audio/music-service-c/s"
  "?keyword={keyword}&page={page}&pagesize={page_size}"
)
INFO_API = "https://www.bilibili.com/audio/music-service-c/web/song/info?sid={id}"


@dataclass
class BilibiliMusic(Music):
  id: int
  picture_url: str

  async def segment(self) -> MessageSegment:
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "bilibili",
      "url": f"https://www.bilibili.com/audio/au{self.id}",
      "audio": "",
      "title": self.name,
      "content": self.artists,
      "image": self.picture_url
    })

  @staticmethod
  async def from_id(id: str) -> MessageSegment:
    if id.startswith("au") or id.startswith("AU") or id.startswith("Au"):
      id_int = int(id[2:])
    else:
      id_int = int(id)
    http = misc.http()
    async with http.get(INFO_API.format(id=id_int)) as response:
      data = await response.json()
    if data["data"] is None:
      raise ValueError("ID不存在")
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "bilibili",
      "url": f"https://www.bilibili.com/audio/au{id_int}",
      "audio": "",
      "title": data["data"]["title"],
      "content": data['data']['author'],
      "image": data["data"]["cover"]
    })

  @staticmethod
  async def search(keyword: str, page_size: int) -> SearchResult["BilibiliMusic"]:
    http = misc.http()
    keyword = encodeuri(keyword)
    async with http.get(
      SEARCH_API.format(keyword=keyword, page=1, page_size=page_size)
    ) as response:
      data = await response.json()
    pages = data["data"]["num_pages"]
    count = pages * data["data"]["pagesize"]

    async def _musics() -> AsyncGenerator[BilibiliMusic, None]:
      nonlocal data
      page = 1
      while True:
        for song in data["data"]["result"]:
          yield BilibiliMusic(
            song["title"],
            song["author"],
            "",
            False,
            song["id"],
            song["cover"],
          )
        page += 1
        if page > pages:
          break
        async with http.get(
          SEARCH_API.format(keyword=keyword, page=page, page_size=page_size)
        ) as response:
          data = await response.json()

    return SearchResult(count, _musics())
