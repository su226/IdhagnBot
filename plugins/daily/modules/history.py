import json
from datetime import date
from typing import List

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import misc

from . import DailyCache, Module

HISTORY_API = "https://baike.baidu.com/cms/home/eventsOnHistory/{month}.json"


class HistoryCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("history.json")

  async def update(self) -> None:
    http = misc.http()
    today = date.today()
    month = f"{today.month:02}"
    day = f"{month}{today.day:02}"
    async with http.get(HISTORY_API.format(month=month)) as response:
      data = await response.json(content_type="text/json")
      data = data[month][day]
      for i in data:
        i["title"] = misc.HTMLStripper.strip(i["title"])
    with open(self.path, "w") as f:
      json.dump(data, f, ensure_ascii=False)
    self.write_date()


cache = HistoryCache()


class HistoryModule(Module):
  async def raw_format(self) -> str:
    await cache.ensure()
    today = date.today()
    lines = [f"今天是{today.month}月{today.day}日，历史上的今天是："]
    with open(cache.path) as f:
      data = json.load(f)
    for i in data:
      lines.append(f"{i['year']} - {i['title']}")
    return "\n".join(lines)

  async def format(self) -> List[Message]:
    text = await self.raw_format()
    text += "\n你可以发送 /历史 再次查看"
    return [Message(MessageSegment.text(text))]
