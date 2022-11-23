import json
import os
from typing import List

from nonebot.adapters.onebot.v11 import Message

from util import misc

from . import DailyCache, Module

EVERYFURRY_API = "https://bot.hifurry.cn/everyfurry?date=today"


class EveryFurryCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("everyfurry.json")
    self.image_path = os.path.splitext(self.path)[0] + ".jpg"

  async def update(self) -> None:
    http = misc.http()
    async with http.get(EVERYFURRY_API) as response:
      data = await response.json()
    with open(self.path, "w") as f:
      json.dump(data, f, ensure_ascii=False)
    if data["StateCode"] == 1:
      async with http.get(data["PictureUrl"]) as response:
        data = await response.read()
      with open(self.image_path, "wb") as f:
        f.write(data)
    self.write_date()


cache = EveryFurryCache()


class EveryFurryModule(Module):
  async def format(self) -> List[Message]:
    await cache.ensure()
    with open(cache.path) as f:
      data = json.load(f)
    if data["StateCode"] == 0:
      return []
    text = f'''
======== 今日兽兽 ========
简介：{data["WorkInformation"]}
作者：{data["AuthorName"]}
详情：https://furry.lihouse.xyz/index.php?ftime={data["Date"]}
来源：{data["SourceLink"]}'''
    return [misc.local("image", cache.image_path) + text]
