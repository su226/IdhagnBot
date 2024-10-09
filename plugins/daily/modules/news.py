from typing import List

from nonebot.adapters.onebot.v11 import Message

from util import misc

from . import DailyCache, Module

NEWS_API = "https://api.tangdouz.com/60.php"


class NewsCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("news.png")

  async def update(self) -> None:
    http = misc.http()
    with open(self.path, "wb") as f:
      async with http.get(NEWS_API) as response:
        url = await response.text()
      async with http.get(url) as response:
        f.write(await response.read())
    self.write_date()


news_cache = NewsCache()


class NewsModule(Module):
  async def format(self) -> List[Message]:
    await news_cache.ensure()
    return [misc.local("image", news_cache.path) + "\n你可以发送 /60秒 再次查看"]
