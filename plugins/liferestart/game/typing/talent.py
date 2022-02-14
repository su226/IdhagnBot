from typing import Literal, TypedDict
from typing_extensions import NotRequired
from .commons import WeightsList

class TalentEffectDict(TypedDict, total=False):
  RDM: int
  CHR: int
  INT: int
  STR: int
  MNY: int
  SPR: int

class GradeReplacementDict(TypedDict):
  grade: list[int]

class TalentReplacementDict(TypedDict):
  talent: WeightsList

class TalentDict(TypedDict):
  id: int | str
  name: str
  description: str
  grade: Literal[0, 1, 2, 3]
  status: NotRequired[int]
  effect: NotRequired[TalentEffectDict]
  condition: NotRequired[str]
  exclude: NotRequired[list[int | str]]
  replacement: NotRequired[GradeReplacementDict | TalentReplacementDict]
  exclusive: NotRequired[Literal[0, 1]]
