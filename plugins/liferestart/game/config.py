from dataclasses import dataclass, field
from functools import cached_property
from typing import ClassVar, Dict, List, Tuple

from .struct.commons import Rarity


@dataclass
class StatRarityItem:
  min: int
  rarity: Rarity
  message_id: str = ""


@dataclass
class StatRarity:
  event_percentage: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON),
    StatRarityItem(20, Rarity.UNCOMMON),
    StatRarityItem(40, Rarity.RARE),
    StatRarityItem(60, Rarity.LEGENDARY),
  ])
  talent_percentage: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON),
    StatRarityItem(30, Rarity.UNCOMMON),
    StatRarityItem(60, Rarity.RARE),
    StatRarityItem(90, Rarity.LEGENDARY),
  ])
  finished_games: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON, "finished_games_0"),
    StatRarityItem(10, Rarity.UNCOMMON, "finished_games_1"),
    StatRarityItem(30, Rarity.UNCOMMON, "finished_games_2"),
    StatRarityItem(50, Rarity.RARE, "finished_games_3"),
    StatRarityItem(70, Rarity.RARE, "finished_games_4"),
    StatRarityItem(100, Rarity.LEGENDARY, "finished_games_5"),
  ])
  achievements: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON, "achievements_0"),
    StatRarityItem(10, Rarity.UNCOMMON, "achievements_1"),
    StatRarityItem(30, Rarity.UNCOMMON, "achievements_2"),
    StatRarityItem(50, Rarity.RARE, "achievements_3"),
    StatRarityItem(70, Rarity.RARE, "achievements_4"),
    StatRarityItem(100, Rarity.LEGENDARY, "achievements_5"),
  ])
  charm: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON, "common_0"),
    StatRarityItem(1, Rarity.COMMON, "common_1"),
    StatRarityItem(2, Rarity.COMMON, "common_2"),
    StatRarityItem(4, Rarity.COMMON, "common_3"),
    StatRarityItem(7, Rarity.UNCOMMON, "common_4"),
    StatRarityItem(9, Rarity.RARE, "common_5"),
    StatRarityItem(11, Rarity.LEGENDARY, "common_6"),
  ])
  money: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON, "common_0"),
    StatRarityItem(1, Rarity.COMMON, "common_1"),
    StatRarityItem(2, Rarity.COMMON, "common_2"),
    StatRarityItem(4, Rarity.COMMON, "common_3"),
    StatRarityItem(7, Rarity.UNCOMMON, "common_4"),
    StatRarityItem(9, Rarity.RARE, "common_5"),
    StatRarityItem(11, Rarity.LEGENDARY, "common_6"),
  ])
  spirit: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON, "spirit_0"),
    StatRarityItem(1, Rarity.COMMON, "spirit_1"),
    StatRarityItem(2, Rarity.COMMON, "spirit_2"),
    StatRarityItem(4, Rarity.COMMON, "spirit_3"),
    StatRarityItem(7, Rarity.UNCOMMON, "spirit_4"),
    StatRarityItem(9, Rarity.RARE, "spirit_5"),
    StatRarityItem(11, Rarity.LEGENDARY, "spirit_6"),
  ])
  intelligence: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON, "common_0"),
    StatRarityItem(1, Rarity.COMMON, "common_1"),
    StatRarityItem(2, Rarity.COMMON, "common_2"),
    StatRarityItem(4, Rarity.COMMON, "common_3"),
    StatRarityItem(7, Rarity.UNCOMMON, "common_4"),
    StatRarityItem(9, Rarity.RARE, "common_5"),
    StatRarityItem(11, Rarity.LEGENDARY, "common_6"),
    StatRarityItem(21, Rarity.LEGENDARY, "intelligence_7"),
    StatRarityItem(131, Rarity.LEGENDARY, "intelligence_8"),
    StatRarityItem(501, Rarity.LEGENDARY, "intelligence_9"),
  ])
  strength: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON, "common_0"),
    StatRarityItem(1, Rarity.COMMON, "common_1"),
    StatRarityItem(2, Rarity.COMMON, "common_2"),
    StatRarityItem(4, Rarity.COMMON, "common_3"),
    StatRarityItem(7, Rarity.UNCOMMON, "common_4"),
    StatRarityItem(9, Rarity.RARE, "common_5"),
    StatRarityItem(11, Rarity.LEGENDARY, "common_6"),
    StatRarityItem(21, Rarity.LEGENDARY, "strength_7"),
    StatRarityItem(101, Rarity.LEGENDARY, "strength_8"),
    StatRarityItem(401, Rarity.LEGENDARY, "strength_9"),
    StatRarityItem(1001, Rarity.LEGENDARY, "strength_10"),
    StatRarityItem(2001, Rarity.LEGENDARY, "strength_11"),
  ])
  age: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON, "age_0"),
    StatRarityItem(1, Rarity.COMMON, "age_1"),
    StatRarityItem(10, Rarity.COMMON, "age_2"),
    StatRarityItem(18, Rarity.COMMON, "age_3"),
    StatRarityItem(40, Rarity.COMMON, "age_4"),
    StatRarityItem(60, Rarity.UNCOMMON, "age_5"),
    StatRarityItem(70, Rarity.UNCOMMON, "age_6"),
    StatRarityItem(80, Rarity.RARE, "age_7"),
    StatRarityItem(90, Rarity.RARE, "age_8"),
    StatRarityItem(95, Rarity.LEGENDARY, "age_9"),
    StatRarityItem(100, Rarity.LEGENDARY, "age_10"),
    StatRarityItem(500, Rarity.LEGENDARY, "age_11"),
  ])
  overall: List[StatRarityItem] = field(default_factory=lambda: [
    StatRarityItem(0, Rarity.COMMON, "common_0"),
    StatRarityItem(41, Rarity.COMMON, "common_1"),
    StatRarityItem(50, Rarity.COMMON, "common_2"),
    StatRarityItem(60, Rarity.COMMON, "common_3"),
    StatRarityItem(80, Rarity.UNCOMMON, "common_4"),
    StatRarityItem(100, Rarity.RARE, "common_5"),
    StatRarityItem(110, Rarity.LEGENDARY, "common_6"),
    StatRarityItem(120, Rarity.LEGENDARY, "common_7"),
  ])
  messages: Dict[str, str] = field(default_factory=lambda: {
    "common_0": "地狱",
    "common_1": "折磨",
    "common_2": "不佳",
    "common_3": "普通",
    "common_4": "优秀",
    "common_5": "罕见",
    "common_6": "逆天",
    "common_7": "传说",

    "spirit_0": "地狱",
    "spirit_1": "折磨",
    "spirit_2": "不幸",
    "spirit_3": "普通",
    "spirit_4": "幸福",
    "spirit_5": "极乐",
    "spirit_6": "天命",

    "age_0": "胎死腹中",
    "age_1": "早夭",
    "age_2": "少年",
    "age_3": "盛年",
    "age_4": "中年",
    "age_5": "花甲",
    "age_6": "古稀",
    "age_7": "杖朝",
    "age_8": "南山",
    "age_9": "不老",
    "age_10": "修仙",
    "age_11": "仙寿",

    "intelligence_7": "识海",
    "intelligence_8": "元神",
    "intelligence_9": "仙魂",

    "strength_7": "凝气",
    "strength_8": "筑基",
    "strength_9": "金丹",
    "strength_10": "元婴",
    "strength_11": "仙体",

    "finished_games_0": "抽到紫色概率不变",
    "finished_games_1": "抽到紫色概率翻倍",
    "finished_games_2": "抽到紫色概率三倍",
    "finished_games_3": "抽到紫色概率四倍",
    "finished_games_4": "抽到紫色概率五倍",
    "finished_games_5": "抽到紫色概率六倍",

    "achievements_0": "抽到橙色概率不变",
    "achievements_1": "抽到橙色概率翻倍",
    "achievements_2": "抽到橙色概率三倍",
    "achievements_3": "抽到橙色概率四倍",
    "achievements_4": "抽到橙色概率五倍",
    "achievements_5": "抽到橙色概率六倍",
  })


@dataclass
class Stat:
  rarity: StatRarity = field(default_factory=StatRarity)
  total: int = 20
  min: int = 0
  max: int = 10
  spirit: int = 5


@dataclass
class TalentBoostItem:
  ZERO: ClassVar["TalentBoostItem"]
  ONE: ClassVar["TalentBoostItem"]

  uncommon: int = 0
  rare: int = 0
  legendary: int = 0

  def __add__(self, other: "TalentBoostItem") -> "TalentBoostItem":
    return TalentBoostItem(
      self.uncommon + other.uncommon, self.rare + other.rare, self.legendary + other.legendary)


TalentBoostItem.ZERO = TalentBoostItem(0, 0, 0)
TalentBoostItem.ONE = TalentBoostItem(1, 1, 1)


@dataclass
class TalentWeight:
  total: int = 1000
  uncommon: int = 100
  rare: int = 10
  legendary: int = 1

  @cached_property
  def common(self) -> int:
    return self.total - self.uncommon - self.rare - self.legendary

  def get(self, rarity: Rarity):
    if rarity == Rarity.COMMON:
      return self.common
    if rarity == Rarity.UNCOMMON:
      return self.uncommon
    if rarity == Rarity.RARE:
      return self.rare
    if rarity == Rarity.LEGENDARY:
      return self.legendary
    raise ValueError("Invaild rarity")

  def __mul__(self, boost: TalentBoostItem) -> "TalentWeight":
    return TalentWeight(
      self.total, self.uncommon * boost.uncommon, self.rare * boost.rare,
      self.legendary * boost.legendary)


@dataclass
class TalentBoost:
  finished_games: List[Tuple[int, TalentBoostItem]] = field(default_factory=lambda: [
    (10, TalentBoostItem(rare=1)),
    (30, TalentBoostItem(rare=2)),
    (50, TalentBoostItem(rare=3)),
    (70, TalentBoostItem(rare=4)),
    (100, TalentBoostItem(rare=5)),
  ])
  achievements: List[Tuple[int, TalentBoostItem]] = field(default_factory=lambda: [
    (10, TalentBoostItem(legendary=1)),
    (30, TalentBoostItem(legendary=2)),
    (50, TalentBoostItem(legendary=3)),
    (70, TalentBoostItem(legendary=4)),
    (100, TalentBoostItem(legendary=5)),
  ])


@dataclass
class Talent:
  weight: TalentWeight = field(default_factory=TalentWeight)
  boost: TalentBoost = field(default_factory=TalentBoost)
  limit: int = 3
  choices: int = 10


@dataclass
class Character:
  stat_value_weight: Dict[int, int] = field(default_factory=lambda: {
    0: 1,
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 6,
    6: 5,
    7: 4,
    8: 3,
    9: 2,
    10: 1,
  })
  talent_count_weight: Dict[int, int] = field(default_factory=lambda: {
    1: 1,
    2: 2,
    3: 3,
    4: 2,
    5: 1,
  })
  choices: int = 3


@dataclass
class Config:
  stat: Stat = field(default_factory=Stat)
  talent: Talent = field(default_factory=Talent)
  character: Character = field(default_factory=Character)
