from dataclasses import dataclass
from typing import List

from ..typing.character import CharacterDict


@dataclass
class Character:
  name: str
  talents: List[int]
  # 祖冲之的属性是唯一一个有 float 的
  charm: float  # CHR, 颜值
  intelligence: float  # INT, 智力
  strength: float  # STR, 体质
  money: float  # MNY, 家境


@dataclass
class PresetCharacter(Character):
  id: int

  @staticmethod
  def parse(data: CharacterDict) -> "PresetCharacter":
    property = data["property"]
    return PresetCharacter(
      id=int(data["id"]),
      name=data["name"],
      talents=[int(x) for x in data["talent"]],
      charm=float(property["CHR"]),
      intelligence=float(property["INT"]),
      strength=float(property["STR"]),
      money=float(property["MNY"]),
    )
