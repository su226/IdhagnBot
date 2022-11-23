from typing import List, Literal, TypedDict, Union

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
  grade: List[int]


class TalentReplacementDict(TypedDict):
  talent: WeightsList


class TalentDict(TypedDict):
  id: Union[int, str]
  name: str
  description: str
  grade: Literal[0, 1, 2, 3]
  status: NotRequired[int]
  effect: NotRequired[TalentEffectDict]
  condition: NotRequired[str]
  exclude: NotRequired[List[Union[int, str]]]
  replacement: NotRequired[Union[GradeReplacementDict, TalentReplacementDict]]
  exclusive: NotRequired[Literal[0, 1]]
