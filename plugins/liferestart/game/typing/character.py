from typing import TypedDict

class CharacterPropertyDict(TypedDict):
  CHR: str
  INT: str
  STR: str
  MNY: str

class CharacterDict(TypedDict):
  id: str
  name: str
  property: CharacterPropertyDict
  talent: list[str]
