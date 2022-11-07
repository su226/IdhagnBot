from datetime import date

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from pydantic import BaseModel

from . import Module

_date = date


class Countdown(BaseModel):
  date: _date
  before: str = ""
  exact: str = ""
  after: str = ""


class CountdownModule(Module):
  def __init__(self, countdowns: list[Countdown]) -> None:
    self.countdowns = countdowns

  async def format(self) -> list[Message]:
    lines = ["今天是："]
    today = date.today()
    for countdown in self.countdowns:
      delta = (countdown.date - today).days
      if delta > 0 and countdown.before:
        lines.append(countdown.before.format(delta))
      elif delta == 0 and countdown.exact:
        lines.append(countdown.exact)
      elif delta < 0 and countdown.after:
        lines.append(countdown.after.format(-delta))
    return [Message(MessageSegment.text("\n".join(lines)))]
