from nonebot.adapters.onebot.v11 import Message

from util import util

from . import DailyCache, Module

NEWS_API = "https://api.qqsuu.cn/api/dm-60s"


class NewsCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("news.png")

  async def update(self) -> None:
    http = util.http()
    with open(self.path, "wb") as f:
      async with http.get(NEWS_API) as response:
        f.write(await response.read())
    self.write_date()


news_cache = NewsCache()


class NewsModule(Module):
  async def format(self) -> Message:
    await news_cache.ensure()
    return util.local_image(news_cache.path) \
      + "你可以发送 /60秒 再次查看"
