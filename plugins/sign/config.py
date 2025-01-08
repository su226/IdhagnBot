from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Literal, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from util.configs import GroupState, SharedConfig


class Config(BaseModel):
  coin: Union[Tuple[int, int], int] = (80, 120)
  combo_each: float = 0.1
  combo_max: float = 1.0
  first_award: List[float] = Field(default_factory=lambda: [0.5, 0.25, 0.1])
  first_prefix: List[str] = Field(default_factory=lambda: ["🥇", "🥈", "🥉"])
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
  calendar: Set[int] = Field(default_factory=set)
  time: datetime = datetime.min


class GroupData(BaseModel):
  users: Dict[int, UserData] = Field(default_factory=dict)
  rank: List[int] = Field(default_factory=list)
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

  def update(self) -> None:
    now = datetime.now()
    if self.time.date() != now.date():
      self.rank = []
    self.time = now


@dataclass
class FormatData:
  uid: int
  gid: int
  coin: int
  original_coin: int
  combo_bonus: Optional[float]
  rank_bonus: Optional[float]


CONFIG = SharedConfig("sign", Config)
STATE = GroupState("sign", GroupData)
