import re
from dataclasses import dataclass
from typing import Literal, Set, Union, cast

from ..condition import Condition
from ..typing.talent import GradeReplacementDict, TalentDict, TalentReplacementDict
from .commons import EmptyDict, Rarity, Weights, parse_weights

MAX_EXECUTE_RE = re.compile(r"AGE\s*\?\s*\[((?:\s*(?:\d+)\s*,)*\s*(?:\d+))\s*,?\s*\]")


@dataclass
class Talent:
  # 基本属性
  id: int
  name: str
  description: str
  rarity: Rarity  # grade

  # 效果
  charm: int  # CHR, 颜值
  intelligence: int  # INT, 智力
  strength: int  # STR, 体质
  money: int  # MNY, 家境
  spirit: int  # SPR, 快乐
  random: int  # RDM, 随机
  points: int  # 初始属性点

  # 条件
  condition: Condition
  max_execute: int
  exclusive: bool
  imcompatible: Set[int]  # exclude
  replacement: Literal[None, "rarity", "talent"]
  weights: Weights

  @staticmethod
  def parse(data: TalentDict) -> "Talent":
    effect = data.get("effect", {})
    replacement: Union[GradeReplacementDict, TalentReplacementDict, EmptyDict] = (
      data.get("replacement", EmptyDict())
    )
    condition = data.get("condition", "")
    if "grade" in replacement:
      replacement_type = "rarity"
      replacement_weights = parse_weights(cast(GradeReplacementDict, replacement)["grade"])
    elif "talent" in replacement:
      replacement_type = "talent"
      replacement_weights = parse_weights(cast(TalentReplacementDict, replacement)["talent"])
    else:
      replacement_type = None
      replacement_weights = {}
    if match := MAX_EXECUTE_RE.search(condition):
      max_execute = len(match[1].split(","))
    else:
      max_execute = 1
    return Talent(
      id=int(data["id"]),
      name=data["name"],
      description=data["description"],
      rarity=Rarity(data["grade"]),
      charm=effect.get("CHR", 0),
      intelligence=effect.get("INT", 0),
      strength=effect.get("STR", 0),
      money=effect.get("MNY", 0),
      spirit=effect.get("SPR", 0),
      random=effect.get("RDM", 0),
      points=data.get("status", 0),
      condition=Condition.parse(condition) if condition else Condition.TRUE,
      max_execute=max_execute,
      exclusive=bool(data.get("exclusive", 0)),
      imcompatible=set(map(int, data.get("exclude", []))),
      replacement=replacement_type,
      weights=replacement_weights,
    )

  def is_imcompatible_with(self, other: "Talent") -> bool:
    return other.id in self.imcompatible or self.id in other.imcompatible
