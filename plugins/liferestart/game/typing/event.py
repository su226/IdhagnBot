from typing import Literal, TypedDict

from typing_extensions import NotRequired


class EventEffectDict(TypedDict, total=False):
  LIF: int
  AGE: int
  CHR: int
  INT: int
  STR: int
  MNY: int
  SPR: int


class EventDict(TypedDict):
  id: int
  event: str
  postEvent: NotRequired[str]
  grade: NotRequired[Literal[0, 1, 2, 3]]
  effect: NotRequired[EventEffectDict]
  NoRandom: NotRequired[Literal[0, 1]]
  branch: NotRequired[list[str]]
  include: NotRequired[str]
  exclude: NotRequired[str]
