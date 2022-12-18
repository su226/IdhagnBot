import math
from dataclasses import dataclass
from typing import AsyncGenerator
import html
from urllib.parse import quote as encodeuri

from nonebot.adapters.onebot.v11 import MessageSegment

from util import misc

from .base import Music, SearchResult

SEARCH_API = (
  "https://www.kuwo.cn/api/www/search/searchMusicBykeyWord"
  "?key={keyword}&pn={page}&rn={page_size}"
)
INFO_API = "http://www.kuwo.cn/api/www/music/musicInfo?mid={id}"
PLAY_API = "https://www.kuwo.cn/api/v1/www/music/playUrl?mid={id}"
TOKEN = "3E7JFQ7MRPL"  # 这个是Github上一年前的野生token，似乎token不会失效
REFERER = "http://yinyue.kuwo.cn"


@dataclass
class KuwoMusic(Music):
  id: int
  picture_url: str

  async def segment(self) -> MessageSegment:
    http = misc.http()
    if self.vip:
      audio_url = ""
    else:
      # 似乎 PLAY_API 不需要 CSRF Token 和 Referer
      async with http.get(PLAY_API.format(id=self.id)) as response:
        data = await response.json()
        audio_url = data["data"]["url"]
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "kuwo",
      "url": f"https://www.kuwo.cn/play_detail/{self.id}",
      "audio": audio_url,
      "title": self.name,
      "content": self.artists,
      "image": self.picture_url
    })

  @staticmethod
  async def from_id(id: str) -> MessageSegment:
    id_int = int(id)
    http = misc.http()
    async with http.get(
      INFO_API.format(id=id_int),headers={"csrf": TOKEN}, cookies={"kw_token": TOKEN}
    ) as response:
      data = await response.json()
    if "data" not in data:
      raise ValueError("ID不存在")
    return await KuwoMusic(
      data["data"]["name"],
      data["data"]["artist"],
      data["data"]["album"],
      data["data"]["isListenFee"],
      data["data"]["rid"],
      data["data"]["pic"]
    ).segment()

  @staticmethod
  async def search(keyword: str, page_size: int) -> SearchResult["KuwoMusic"]:
    http = misc.http()
    keyword = encodeuri(keyword)
    async with http.get(
      SEARCH_API.format(keyword=keyword, page=0, page_size=page_size),
      headers={"csrf": TOKEN, "Referer": REFERER}, cookies={"kw_token": TOKEN}
    ) as response:
      data = await response.json()
    count = int(data["data"]["total"])
    pages = math.ceil(count / page_size)

    async def _musics() -> AsyncGenerator[KuwoMusic, None]:
      nonlocal data
      page = 0
      while True:
        for song in data["data"]["list"]:
          yield KuwoMusic(
            html.unescape(song["name"]),
            html.unescape(song["artist"]),
            html.unescape(song["album"]),
            song["isListenFee"],
            song["rid"],
            song["pic"],
          )
        page += 1
        if page >= pages:
          break
        async with http.get(
          SEARCH_API.format(keyword=keyword, page=page, page_size=page_size),
          headers={"csrf": TOKEN, "Referer": REFERER}, cookies={"kw_token": TOKEN}
        ) as response:
          data = await response.json()

    return SearchResult(count, _musics())
