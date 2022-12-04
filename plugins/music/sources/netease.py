import math
from dataclasses import dataclass
from typing import AsyncGenerator
from urllib.parse import quote as encodeuri

from nonebot.adapters.onebot.v11 import MessageSegment

from util import misc

from .base import Music, SearchResult

API = "https://music.163.com/api/search/get/web?type=1&offset={offset}&limit={limit}&s={keyword}"
LIMIT = 10


@dataclass
class NeteaseMusic(Music):
  id: int

  def segment(self) -> MessageSegment:
    return MessageSegment.music("163", self.id)

  @staticmethod
  async def search(keyword: str) -> SearchResult["NeteaseMusic"]:
    http = misc.http()
    async with http.get(
      API.format(keyword=encodeuri(keyword), offset=0, limit=LIMIT)
    ) as response:
      data = await response.json(content_type=None)
    count = data["result"]["songCount"]
    pages = math.ceil(count / LIMIT)

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
          API.format(keyword=encodeuri(keyword), offset=page * LIMIT, limit=LIMIT)
        ) as response:
          data = await response.json(content_type=None)

    return SearchResult(count, _musics())
