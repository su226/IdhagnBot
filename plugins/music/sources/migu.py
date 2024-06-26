import math
import re
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional, Tuple
from urllib.parse import quote as encodeuri, urlparse, urlunparse

from nonebot.adapters.onebot.v11 import MessageSegment

from util import misc

from .base import Music, SearchResult

SEARCH_API = (
  "https://m.music.migu.cn/migumusic/h5/search/all"
  "?text={keyword}&pageNo={page}&pageSize={page_size}"
)
SEARCH_HEADERS = {
  "User-Agent": (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
  ),
  "By": "1c2fc886e2a3fbd1fb75dcb47a070ba3",  # 必须是 User-Agent 的 MD5
  "Referer": "https://m.music.migu.cn/v4/search",
}
INFO_API = (
  "https://c.musicapp.migu.cn/MIGUM2.0/v1.0/content/resourceinfo.do"
  "?copyrightId={id}&resourceType=2"
)
ID_RE = re.compile("[0-9A-Z]{11}")


@dataclass
class MiguMusic(Music):
  id: str
  picture_url: str

  @staticmethod
  def _fix_url(url: str) -> str:
    # 原本是ftp，替换为https
    return urlunparse(urlparse(url)._replace(scheme="https", netloc="freetyst.nf.migu.cn"))

  @staticmethod
  def _get_best_url(data: Dict[str, Any]) -> Tuple[Optional[str], str]:
    formats = data["newRateFormats"] or data["rateFormats"]
    if formats[-1]["formatType"] == "SQ":
      lossless_format = formats[-1]
      lossy_format = formats[-2]
    else:
      lossless_format = None
      lossy_format = formats[-1]
    lossless_url = MiguMusic._fix_url(lossless_format["androidUrl"]) if lossless_format else None
    lossy_url = MiguMusic._fix_url(lossy_format["url"])
    return lossless_url, lossy_url

  async def segment(self) -> MessageSegment:
    http = misc.http()
    async with http.get(INFO_API.format(id=self.id)) as response:
      data = await response.json()
      song = data["resource"][0]
    lossless_url, lossy_url = self._get_best_url(song)
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "migu",
      "url": f"https://music.migu.cn/v3/music/song/{self.id}",
      "audio": lossy_url,
      "lossless": lossless_url,
      "title": song["songName"],
      "content": song["singer"],
      "image": song["albumImgs"][0]["img"],
    })

  @staticmethod
  async def from_id(id: str) -> MessageSegment:
    if not ID_RE.fullmatch(id):
      raise ValueError("无效ID")
    http = misc.http()
    async with http.get(INFO_API.format(id=id)) as response:
      data = await response.json()
      if not data["resource"]:
        raise ValueError("ID不存在")
      song = data["resource"][0]
    lossless_url, lossy_url = MiguMusic._get_best_url(song)
    return MessageSegment("music", {
      "type": "custom",
      "subtype": "migu",
      "url": f"https://music.migu.cn/v3/music/song/{id}",
      "audio": lossy_url,
      "lossless": lossless_url,
      "title": song["songName"],
      "content": song["singer"],
      "image": song["albumImgs"][0]["img"],
    })

  @staticmethod
  async def search(keyword: str, page_size: int) -> SearchResult["MiguMusic"]:
    http = misc.http()
    keyword = encodeuri(keyword)
    async with http.get(
      SEARCH_API.format(keyword=keyword, page=1, page_size=page_size),
      headers=SEARCH_HEADERS,
    ) as response:
      data = await response.json(content_type=None)
    count = data["data"]["songsData"]["total"]
    pages = math.ceil(count / page_size)

    async def _musics() -> AsyncGenerator[MiguMusic, None]:
      nonlocal data
      page = 1
      while True:
        for song in data["data"]["songsData"]["items"]:
          yield MiguMusic(
            song["name"],
            "/".join(x["name"] for x in song["singers"]),
            album["name"] if (album := song["album"]) else "",
            False,  # INFO_API 可以读到 VIP 歌曲的直链（包括 FLAC）
            song["copyrightId"],
            "https://" + cover if (cover := song["largePic"]) else "",
          )
        page += 1
        if page > pages:
          break
        async with http.get(
          SEARCH_API.format(keyword=keyword, page=page, page_size=page_size),
          headers=SEARCH_HEADERS,
        ) as response:
          data = await response.json(content_type=None)

    return SearchResult(count, _musics())
