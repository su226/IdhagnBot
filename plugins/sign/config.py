from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from util.config_v2 import GroupState, SharedConfig


class Config(BaseModel):
  coin: int | tuple[int, int] = (80, 120)
  combo_each: float = 0.1
  combo_max: float = 1.0
  first_award: list[int] = Field(default_factory=lambda: [0.5, 0.25, 0.1])
  first_prefix: list[str] = Field(default_factory=lambda: ["🥇", "🥈", "🥉"])
  max_rank: int = 10
  formatter: Literal["legacy", "ring"] = "ring"

  @property
  def min_coin(self):
    if isinstance(self.coin, int):
      return self.coin
    return self.coin[0]

  @property
  def max_coin(self):
    if isinstance(self.coin, int):
      return self.coin
    return self.coin[1]


class UserData(BaseModel):
  combo_days: int = 0
  total_days: int = 0
  calendar: set[int] = Field(default_factory=set)
  time: datetime = datetime.min


class GroupData(BaseModel):
  users: dict[int, UserData] = Field(default_factory=dict)
  rank: list[int] = Field(default_factory=list)
  time: datetime = datetime.min

  def get_user(self, uid: int) -> UserData:
    if uid not in self.users:
      self.users[uid] = UserData()
    user_data = self.users[uid]
    sign_date = user_data.time.date()
    today = date.today()
    if sign_date.year != today.year or sign_date.month != today.month:
      user_data.calendar.clear()
    return user_data


@dataclass
class FormatData:
  uid: int
  gid: int
  coin: int
  original_coin: int
  combo_bonus: float | None
  rank_bonus: float | None


CONFIG = SharedConfig("sign", Config)
STATE = GroupState("sign", GroupData)
