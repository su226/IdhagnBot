from ..typing.event import EventDict
from .commons import Rarity
from ..condition import Condition
from dataclasses import dataclass

@dataclass()
class Event:
  id: int
  event: str
  post: str
  rarity: Rarity

  life: int # LIF, 生命
  age: int # AGE, 年龄
  charm: int # CHR, 颜值
  intelligence: int # INT, 智力
  strength: int # STR, 体质
  money: int # MNY, 家境
  spirit: int # SPR, 快乐

  no_random: bool
  branch: list[tuple[int, Condition]]
  include: Condition
  exclude: Condition

  @staticmethod
  def parse(data: EventDict) -> "Event":
    effect = data.get("effect", {})
    include = data.get("include", "")
    exclude = data.get("exclude", "")
    return Event(
      id=data["id"],
      event=data["event"],
      post=data.get("postEvent", ""),
      rarity=Rarity(data.get("grade", 0)),
      life=effect.get("LIF", 0),
      age=effect.get("AGE", 0),
      charm=effect.get("CHR", 0),
      intelligence=effect.get("INT", 0),
      strength=effect.get("STR", 0),
      money=effect.get("MNY", 0),
      spirit=effect.get("SPR", 0),
      no_random=bool(data.get("NoRandom", 0)),
      branch=[(int(id), Condition.parse(cond)) for cond, id in map(lambda x: x.split(":"), data.get("branch", []))],
      include=Condition.parse(include) if include else Condition.TRUE,
      exclude=Condition.parse(exclude) if exclude else Condition.FALSE,
    )
