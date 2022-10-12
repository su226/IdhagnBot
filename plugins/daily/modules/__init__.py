import asyncio
import os
from datetime import date

from util import util


class Module:
  async def format(self) -> util.AnyMessage:
    raise NotImplementedError


class DailyCache:
  def __init__(self, filename: str) -> None:
    self.lock = asyncio.Lock()
    self.path = os.path.abspath(f"states/daily_cache/{filename}")
    self.date_path = os.path.splitext(self.path)[0] + ".date"

  def check(self) -> bool:
    if not (os.path.exists(self.path) and os.path.exists(self.date_path)):
      return False
    with open(self.date_path) as f:
      update_date = date.fromisoformat(f.read())
    return update_date == date.today()

  def write_date(self) -> None:
    with open(self.date_path, "w") as f:
      f.write(date.today().isoformat())

  async def update(self) -> None:
    raise NotImplementedError

  async def ensure(self) -> None:
    if not self.check():
      async with self.lock:
        if not self.check():
          os.makedirs(os.path.dirname(self.path), exist_ok=True)
          await self.update()
