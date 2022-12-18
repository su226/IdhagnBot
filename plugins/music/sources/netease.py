import math
from dataclasses import dataclass
from typing import AsyncGenerator
from urllib.parse import quote as encodeuri

from nonebot.adapters.onebot.v11 import MessageSegment

from util import misc

from .base import Music, SearchResult

SEARCH_API = (
  "https://music.163.com/api/search/get/web?type=1&offset={offset}&limit={limit}&s={keyword}"
)
INFO_API = "http://music.163.com/api/song/detail/?ids=[{id}]"


@dataclass
class NeteaseMusic(Music):
  id: int

  async def segment(self) -> MessageSegment:
    http = misc.http()
    async with http.get(INFO_API.format(id=self.id)) as response:
      data = await response.json(content_type=None)
      song = data["songs"][0]
      audio = "" if song["fee"] == 1 else f"http://music.163.com/song/media/outer/url?id={self.id}"
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "163",
      "url": f"https://music.163.com/#/song?id={song['id']}",
      "audio": audio,
      "title": song["name"],
      "content": song["artists"][0]["name"],
      "image": song["album"]["picUrl"]
    })

  @staticmethod
  async def from_id(id: str) -> MessageSegment:
    id_int = int(id)
    http = misc.http()
    async with http.get(INFO_API.format(id=id_int)) as response:
      data = await response.json(content_type=None)
      if not data["songs"]:
        raise ValueError("ID不存在")
      song = data["songs"][0]
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "163",
      "url": f"https://music.163.com/#/song?id={id}",
      "audio": "" if song["fee"] == 1 else f"http://music.163.com/song/media/outer/url?id={id}",
      "title": song["name"],
      "content": song["artists"][0]["name"],
      "image": song["album"]["picUrl"]
    })

  @staticmethod
  async def search(keyword: str, page_size: int) -> SearchResult["NeteaseMusic"]:
    http = misc.http()
    keyword = encodeuri(keyword)
    async with http.get(
      SEARCH_API.format(keyword=keyword, offset=0, limit=page_size)
    ) as response:
      data = await response.json(content_type=None)
    count = data["result"]["songCount"]
    pages = math.ceil(count / page_size)

    async def _musics() -> AsyncGenerator[NeteaseMusic, None]:
      nonlocal data
      page = 0
      while True:
        for song in data["result"]["songs"]:
          yield NeteaseMusic(
            song["name"],
            "/".join(x["name"] for x in song["artists"]),
            song["album"]["name"],
            song["fee"] == 1,
            song["id"],
          )
        page += 1
        if page >= pages:
          break
        async with http.get(
          SEARCH_API.format(keyword=keyword, offset=page * page_size, limit=page_size)
        ) as response:
          data = await response.json(content_type=None)

    return SearchResult(count, _musics())
