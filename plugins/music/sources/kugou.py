import hashlib
import math
import re
from dataclasses import dataclass
from typing import AsyncGenerator, Dict

from nonebot.adapters.onebot.v11 import MessageSegment

from util import misc

from .base import Music, SearchResult

TOKEN = "NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt"  # 调试器抓到的，签名用
SEARCH_API = "https://complexsearch.kugou.com/v2/search/song"
SEARCH_PARAMS = {
  "srcappid": "2919",
  "clientver": "1000",
  "mid": "1",  # 似乎 mid 和 dfid 乱填一个也行
  "dfid": "1",
  "keyword": "",
  "page": "1",
  "pagesize": "30",
  "userid": "0",
  "appid": "1014",  # 没有这个参数也能搜索，但是没有 EMixSongID
  "signature": "",
}
INFO_API = "https://wwwapi.kugou.com/yy/index.php?r=play/getdata&encode_album_audio_id={id}"
ID_RE = re.compile(r"[a-z0-9]{8}")


def sign(params: Dict[str, str]) -> Dict[str, str]:
  del params["signature"]
  params_str = "".join(sorted(f"{k}={v}" for k, v in params.items()))
  params["signature"] = hashlib.md5(f"{TOKEN}{params_str}{TOKEN}".encode()).hexdigest()
  return params


@dataclass
class KugouMusic(Music):
  id: str

  async def segment(self) -> MessageSegment:
    http = misc.http()
    cookies = {"kg_mid": SEARCH_PARAMS["mid"]}
    async with http.get(INFO_API.format(id=self.id), cookies=cookies) as response:
      data = await response.json(content_type=None)
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "kugou",
      "url": f"https://www.kugou.com/mixsong/{self.id}.html",
      "audio": data["data"]["play_url"],
      "title": self.name,
      "content": self.artists,
      "image": data["data"]["img"],
    })

  @staticmethod
  async def from_id(id: str) -> MessageSegment:
    if not ID_RE.fullmatch(id):
      raise ValueError("无效ID")
    http = misc.http()
    cookies = {"kg_mid": SEARCH_PARAMS["mid"]}
    async with http.get(INFO_API.format(id=id), cookies=cookies) as response:
      data = await response.json(content_type=None)
    if not data["data"]:
      raise ValueError("ID不存在")
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "kugou",
      "url": f"https://www.kugou.com/mixsong/{id}.html",
      "audio": data["data"]["play_url"],
      "title": data["data"]["song_name"],
      "content": data["data"]["author_name"],
      "image": data["data"]["img"],
    })

  @staticmethod
  async def search(keyword: str, page_size: int) -> SearchResult["KugouMusic"]:
    http = misc.http()
    params = SEARCH_PARAMS.copy()
    params["keyword"] = keyword
    params["pagesize"] = str(page_size)
    async with http.get(SEARCH_API, params=sign(params)) as response:
      data = await response.json(content_type=None)
    count = data["data"]["total"]
    pages = math.ceil(count / page_size)

    async def _musics() -> AsyncGenerator[KugouMusic, None]:
      nonlocal data
      page = 1
      while True:
        for song in data["data"]["lists"]:
          yield KugouMusic(
            song["SongName"],
            song["SingerName"],
            song["AlbumName"],
            False,
            song["EMixSongID"],
          )
        page += 1
        if page > pages:
          break
        params["page"] = str(page)
        async with http.get(SEARCH_API, params=sign(params)) as response:
          data = await response.json(content_type=None)
    return SearchResult(count, _musics())
