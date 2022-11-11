import json
from datetime import date

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import misc

from . import DailyCache, Module

HISTORY_API = "https://www.ipip5.com/today/api.php?type=json"


class HistoryCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("history.json")

  async def update(self) -> None:
    http = misc.http()
    async with http.get(HISTORY_API) as response:
      data = await response.json()
    data["result"].pop()
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
    for i in data["result"]:
      lines.append(f"{i['year']} - {i['title']}")
    return "\n".join(lines)

  async def format(self) -> list[Message]:
    text = await self.raw_format()
    text += "\n你可以发送 /历史 再次查看"
    return [Message(MessageSegment.text(text))]
