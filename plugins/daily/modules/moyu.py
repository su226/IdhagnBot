from typing import List

from nonebot.adapters.onebot.v11 import Message

from util import misc

from . import DailyCache, Module

MOYU_API = "https://api.j4u.ink/v1/store/other/proxy/remote/moyu.json"


class MoyuCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("moyu.png")

  async def update(self) -> None:
    http = misc.http()
    async with http.get(MOYU_API) as response:
      data = await response.json()
    with open(self.path, "wb") as f:
      async with http.get(data["data"]["img_url"]) as response:
        f.write(await response.read())
    self.write_date()


moyu_cache = MoyuCache()


class MoyuModule(Module):
  async def format(self) -> List[Message]:
    await moyu_cache.ensure()
    return [misc.local("image", moyu_cache.path) + "\n你可以发送 /摸鱼 再次查看"]
