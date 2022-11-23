from dataclasses import dataclass
from typing import List

from ..typing.character import CharacterDict


@dataclass()
class Character:
  id: int
  name: str
  talents: List[int]
  charm: int  # CHR, 颜值
  intelligence: int  # INT, 智力
  strength: int  # STR, 体质
  money: int  # MNY, 家境

  @staticmethod
  def parse(data: CharacterDict) -> "Character":
    property = data["property"]
    return Character(
      id=int(data["id"]),
      name=data["name"],
      talents=[int(x) for x in data["talent"]],
      charm=int(property["CHR"]),
      intelligence=int(property["INT"]),
      strength=int(property["STR"]),
      money=int(property["MNY"]),
    )
