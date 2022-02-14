from typing import Literal, TypedDict

Opportunity = Literal["START", "TRAJECTORY", "SUMMARY", "END"]

class AchievementDict(TypedDict):
  id: int
  name: str
  description: str
  grade: Literal[0, 1, 2, 3]
  condition: str
  hide: Literal[0, 1]
  opportunity: Opportunity
