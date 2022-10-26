import json
from datetime import date, timedelta

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import util

from . import DailyCache, Module

EVERYFURRY_API = "https://bot.hifurry.cn/everyfurry?date="


class EveryFurryCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("everyfurry.json")

  async def update(self) -> None:
    http = util.http()
    today = (date.today() - timedelta(1)).strftime("%Y%m%d")
    async with http.get(EVERYFURRY_API + today) as response:
      data = await response.json()
    with open(self.path, "w") as f:
      json.dump(data, f, ensure_ascii=False)
    self.write_date()


cache = EveryFurryCache()


class EveryFurryModule(Module):
  async def format(self) -> Message:
    await cache.ensure()
    with open(cache.path) as f:
      data = json.load(f)
    msg = (
      MessageSegment.image(data["PictureUrl"])
      + f'''
======== 今日兽兽 ========
简介：{data["WorkInformation"]}
作者：{data["AuthorName"]}
详情：https://furry.lihouse.xyz/index.php?ftime={data["Date"]}
来源：{data["SourceLink"]}'''
    )
    return msg
