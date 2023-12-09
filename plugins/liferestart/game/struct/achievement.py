from dataclasses import dataclass
from enum import Enum

from ..condition import Condition
from ..typing.achievement import AchievementDict
from .commons import Rarity


class Opportunity(Enum):
  START = 0
  TRAJECTORY = 1
  SUMMARY = 2
  END = 2


@dataclass
class Achievement:
  id: int
  name: str
  description: str
  rarity: Rarity
  opportunity: Opportunity
  hidden: bool
  condition: Condition

  @staticmethod
  def parse(data: AchievementDict) -> "Achievement":
    return Achievement(
      id=data["id"],
      name=data["name"],
      description=data["description"],
      rarity=Rarity(data["grade"]),
      opportunity=Opportunity[data["opportunity"]],
      hidden=bool(data["hide"]),
      condition=Condition.parse(data["condition"]),
    )
