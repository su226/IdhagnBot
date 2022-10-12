

import json
from datetime import date

from util import util

from . import DailyCache, Module

HISTORY_API = "https://www.ipip5.com/today/api.php?type=json"


class HistoryCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("history.json")

  async def update(self) -> None:
    http = util.http()
    async with http.get(HISTORY_API) as response:
      data = await response.json()
    data["result"].pop()
    with open(self.path, "w") as f:
      json.dump(data, f, ensure_ascii=False)
    self.write_date()


cache = HistoryCache()


class HistoryModule(Module):
  async def format(self) -> str:
    await cache.ensure()
    today = date.today()
    lines = [f"今天是{today.month}月{today.day}日，历史上的今天是："]
    with open(cache.path) as f:
      data = json.load(f)
    for i in data["result"]:
      lines.append(f"{i['year']} - {i['title']}")
    return "\n".join(lines)
