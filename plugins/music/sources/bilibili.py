from dataclasses import dataclass
from typing import AsyncGenerator
from urllib.parse import quote as encodeuri

from nonebot.adapters.onebot.v11 import MessageSegment

from util import misc
from util.api_common import bilibili_auth

from .base import Music, SearchResult

SEARCH_API = (
  "https://api.bilibili.com/audio/music-service-c/s"
  "?keyword={keyword}&page={page}&pagesize={page_size}"
)
INFO_API = "https://www.bilibili.com/audio/music-service-c/web/song/info?sid={id}"
URL_API = "https://www.bilibili.com/audio/music-service-c/web/url?sid={id}"


@dataclass
class BilibiliMusic(Music):
  id: int
  picture_url: str

  async def segment(self) -> MessageSegment:
    http = misc.http()
    async with http.get(URL_API.format(id=self.id)) as response:
      urldata = await response.json()
      urls = urldata["data"]["cdns"]
    referer = f"https://www.bilibili.com/audio/au{self.id}"
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "bilibili",
      "url": referer,
      "audio": urls[0] if urls else "",
      "title": self.name,
      "content": self.artists,
      "image": self.picture_url,
      "headers": {
        "Referer": referer,
        "User-Agent": misc.BROWSER_UA,
      },
    })

  @staticmethod
  async def from_id(id: str) -> MessageSegment:
    if id.startswith(("au", "AU", "Au")):
      id_int = int(id[2:])
    else:
      id_int = int(id)
    http = misc.http()
    async with http.get(INFO_API.format(id=id_int)) as response:
      data = await response.json()
      if data["code"] == 4511001:
        raise ValueError("ID不存在")
      data = bilibili_auth.ApiError.check(data)
    async with http.get(URL_API.format(id=id_int)) as response:
      urls = bilibili_auth.ApiError.check(await response.json())["cdns"]
    referer = f"https://www.bilibili.com/audio/au{id_int}"
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "bilibili",
      "url": referer,
      "audio": urls[0] if urls else "",
      "title": data["title"],
      "content": data["author"],
      "image": data["cover"],
      "headers": {
        "Referer": referer,
        "User-Agent": misc.BROWSER_UA,
      },
    })

  @staticmethod
  async def search(keyword: str, page_size: int) -> SearchResult["BilibiliMusic"]:
    http = misc.http()
    keyword = encodeuri(keyword)
    async with http.get(
      SEARCH_API.format(keyword=keyword, page=1, page_size=page_size),
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
          SEARCH_API.format(keyword=keyword, page=page, page_size=page_size),
        ) as response:
          data = await response.json()

    return SearchResult(count, _musics())
