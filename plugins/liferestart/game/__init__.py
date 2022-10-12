from collections import defaultdict
from dataclasses import dataclass, field
from random import Random
from typing import Any, Generator, TypedDict

from .config import Config, StatRarityItem, TalentBoostItem
from .data import ACHIEVEMENT, AGE, EVENT, TALENT
from .struct.achievement import Achievement, Opportunity
from .struct.character import Character
from .struct.commons import Rarity
from .struct.event import Event
from .struct.talent import Talent


class SerializedGeneratedCharacter(TypedDict):
  name: str
  talents: list[int]
  charm: int
  intelligence: int
  strength: int
  money: int
  seed: int


@dataclass
class GeneratedCharacter(Character):
  seed: int

  def serialize(self) -> SerializedGeneratedCharacter:
    return {
      "name": self.name,
      "talents": self.talents,
      "charm": self.charm,
      "intelligence": self.intelligence,
      "strength": self.strength,
      "money": self.money,
      "seed": self.seed,
    }

  @staticmethod
  def deserialize(serialized: SerializedGeneratedCharacter) -> "GeneratedCharacter":
    return GeneratedCharacter(
      -1,
      name=serialized["name"],
      talents=serialized["talents"],
      charm=serialized["charm"],
      intelligence=serialized["intelligence"],
      strength=serialized["strength"],
      money=serialized["money"],
      seed=serialized["seed"])


class SerializedStatistics(TypedDict):
  talents: list[int]
  events: list[int]
  achievements: list[int]
  finished_games: int
  inherited_talent: int
  character: SerializedGeneratedCharacter | None


@dataclass  # dirty hack
class Statistics:
  talents: set[int] = field(default_factory=set)
  events: set[int] = field(default_factory=set)
  achievements: set[int] = field(default_factory=set)
  finished_games: int = 0
  inherited_talent: int = -1
  character: GeneratedCharacter | None = None

  def serialize(self) -> SerializedStatistics:
    return {
      "inherited_talent": self.inherited_talent,
      "finished_games": self.finished_games,
      "talents": list(self.talents),
      "events": list(self.events),
      "achievements": list(self.achievements),
      "character": self.character.serialize() if self.character else None,
    }

  @staticmethod
  def deserialize(serialized: SerializedStatistics) -> "Statistics":
    character = serialized["character"]
    return Statistics(
      set(serialized["talents"]),
      set(serialized["events"]),
      set(serialized["achievements"]),
      serialized["finished_games"],
      serialized["inherited_talent"],
      GeneratedCharacter.deserialize(character) if character else None)


@dataclass
class Progress:
  age: int
  talents: list[Talent]
  events: list[tuple[Event, bool]]
  achievements: list[Achievement]
  charm: int
  intelligence: int
  strength: int
  money: int
  spirit: int


@dataclass
class End:
  talents: list[Talent]
  achievements: list[Achievement]
  age: int
  charm: int
  intelligence: int
  strength: int
  money: int
  spirit: int
  overall: int
  summary_age: StatRarityItem
  summary_charm: StatRarityItem
  summary_intelligence: StatRarityItem
  summary_strength: StatRarityItem
  summary_money: StatRarityItem
  summary_spirit: StatRarityItem
  summary_overall: StatRarityItem


class Game:
  config: Config
  statistics: Statistics

  _random: Random

  _raw_talents: list[Talent]
  _talents: list[Talent]
  _charm: int
  _intelligence: int
  _strength: int
  _money: int
  _spirit: int
  _max_charm: int
  _max_intelligence: int
  _max_strength: int
  _max_money: int
  _max_spirit: int
  _min_charm: int
  _min_intelligence: int
  _min_strength: int
  _min_money: int
  _min_spirit: int

  _age: int
  _max_age: int
  _alive: bool
  _talent_executed: dict[int, int]
  _condition_vars: dict[str, Any]

  def __init__(self, config: Config = Config(), statistics: Statistics = Statistics()):
    self.config = config
    self.statistics = statistics
    self._random = Random()
    self._talents = []
    self._charm = self._max_charm = self._min_charm = 0
    self._intelligence = self._max_intelligence = self._min_intelligence = 0
    self._strength = self._max_strength = self._min_strength = 0
    self._money = self._max_money = self._min_money = 0
    self._spirit = self._max_spirit = self._min_spirit = 0
    self._max_age = self._age = -1
    self._alive = True
    self._talent_executed = defaultdict(int)
    self._condition_vars = {
      "ATLT": self.statistics.talents,
      "AEVT": self.statistics.events,
      "TMS": self.statistics.finished_games,
    }

  def seed(self, seed: int | None = None) -> int:
    if seed is None:
      self._random.seed(None)
      seed = int.from_bytes(self._random.randbytes(4), "little")
    self._random.seed(seed)
    return seed

  def random_talents(self) -> Generator[list[Talent], None, None]:
    weight = self.config.talent.weight * sum([
      self._get_boost(self.config.talent.boost.finished_games, self.statistics.finished_games),
      self._get_boost(self.config.talent.boost.achievements, len(self.statistics.achievements)),
    ], TalentBoostItem.ONE)
    by_rarity: dict[Rarity, list[Talent]] = {rarity: [] for rarity in Rarity}
    for i in (i for i in TALENT.values() if not i.exclusive):
      by_rarity[i.rarity].append(i)
    while True:
      result: list[Talent] = []
      while len(result) < self.config.talent.choices:
        rarities: list[Rarity] = []
        weights: list[float] = []
        for rarity in Rarity:
          if by_rarity[rarity]:
            rarities.append(rarity)
            weights.append(weight.get(rarity))
        if not rarities:
          break
        rarity = self._random.choices(rarities, weights)[0]
        talent = self._random.choice(by_rarity[rarity])
        result.append(talent)
        by_rarity[rarity].remove(talent)
      yield list(result)
      for i in result:
        by_rarity[i.rarity].append(i)

  def _get_boost(self, boosts: list[tuple[int, TalentBoostItem]], value: int) -> TalentBoostItem:
    for min, boost in reversed(boosts):
      if value >= min:
        return boost
    return TalentBoostItem.ZERO

  def set_talents(self, talents: list[Talent]) -> list[Talent]:
    self._raw_talents = talents
    self._talents = talents.copy()
    for i, talent in enumerate(self._raw_talents):
      self.statistics.talents.add(talent.id)
      replacement = self._get_replacement(talent)
      if replacement:
        self.statistics.talents.add(replacement.id)
        self._talents[i] = replacement
    self._condition_vars["TLT"] = {talent.id for talent in self._talents}
    return self._talents

  def _get_replacement(self, current: Talent) -> Talent | None:
    if current.replacement == "rarity":
      by_rarity: dict[int, list[Talent]] = {i: [] for i in current.weights}
      for talent in TALENT.values():
        if not talent.exclusive and talent.rarity in current.weights and not any(
          talent is other or talent.is_imcompatible_with(other) for other in self._talents
        ):
          by_rarity[talent.rarity].append(talent)
      rarities: list[int] = []
      weights: list[float] = []
      for id, weight in current.weights.items():
        if by_rarity[id]:
          rarities.append(id)
          weights.append(weight)
      if rarities:
        rarity = self._random.choices(rarities, weights)[0]
        talent = self._random.choice(by_rarity[rarity])
        return talent
    elif current.replacement == "talent":
      choices: list[Talent] = []
      weights: list[float] = []
      for id, weight in current.weights.items():
        talent = TALENT[id]
        if not any(
          talent is other or talent.is_imcompatible_with(other) for other in self._talents
        ):
          choices.append(talent)
          weights.append(weight)
      if choices:
        talent = self._random.choices(choices, weights)[0]
        return talent
    return None

  def get_points(self) -> int:
    return self.config.stat.total + sum(i.points for i in self._talents)

  def set_stats(self, charm: int, intelligence: int, strength: int, money: int):
    self._charm = self._max_charm = self._min_charm = charm
    self._intelligence = self._max_intelligence = self._min_intelligence = intelligence
    self._strength = self._max_strength = self._min_strength = strength
    self._money = self._max_money = self._min_money = money
    self._spirit = self._max_spirit = self._min_spirit = self.config.stat.spirit
    self._update_vars()

  def progress(self) -> Generator[Progress, None, None]:
    self._events: set[int] = set()
    self._condition_vars["EVT"] = self._events
    yield Progress(
      -1,
      self._execute_talents(),
      [],
      self._check_achievements(Opportunity.START),
      self._charm,
      self._intelligence,
      self._strength,
      self._money,
      self._spirit)
    while self._alive:
      self._age += 1
      yield Progress(
        self._age,
        self._execute_talents(),
        self._execute_events(),
        self._check_achievements(Opportunity.TRAJECTORY),
        self._charm,
        self._intelligence,
        self._strength,
        self._money,
        self._spirit)

  def _execute_talents(self) -> list[Talent]:
    talents: list[Talent] = []
    for talent in self._talents:
      if (
        self._talent_executed[talent.id] < talent.max_execute
        and talent.condition(**self._condition_vars)
      ):
        self._add_stats(
          talent.charm, talent.intelligence, talent.strength, talent.money, talent.spirit,
          talent.random)
        self._update_vars()
        self._talent_executed[talent.id] += 1
        talents.append(talent)
    return talents

  def _execute_events(self) -> list[tuple[Event, bool]]:
    events: list[tuple[Event, bool]] = []
    choices: list[Event] = []
    weights: list[float] = []
    for id, weight in AGE[self._age].items():
      event = EVENT[id]
      if (
        not event.no_random and not event.exclude(**self._condition_vars)
        and event.include(**self._condition_vars)
      ):
        choices.append(event)
        weights.append(weight)
    event = self._random.choices(choices, weights)[0]
    while event is not None:
      self._alive = [False, self._alive, True][event.life + 1]
      self._age += event.age
      self._add_stats(
        event.charm, event.intelligence, event.strength, event.money, event.spirit, 0)
      self._update_vars()
      self.statistics.events.add(event.id)
      self._events.add(event.id)
      next_event = None
      for id, cond in event.branch:
        if cond(**self._condition_vars):
          next_event = EVENT[id]
          break
      events.append((event, next_event is not None))
      event = next_event
    return events

  def _check_achievements(self, opportunity: Opportunity) -> list[Achievement]:
    achievements: list[Achievement] = []
    for achievement in ACHIEVEMENT.values():
      if (
        achievement.id not in self.statistics.achievements
        and achievement.opportunity == opportunity
        and achievement.condition(**self._condition_vars)
      ):
        achievements.append(achievement)
        self.statistics.achievements.add(achievement.id)
    return achievements

  def _add_stats(
    self, charm: int, intelligence: int, strength: int, money: int, spirit: int, random: int
  ):
    random_values = [0] * 5
    if random:
      for i in range(5):
        value = self._random.randint(0, random)
        random_values[i] = value
        random -= value
    self._charm += charm + random_values[0]
    self._intelligence += intelligence + random_values[1]
    self._strength += strength + random_values[2]
    self._money += money + random_values[3]
    self._spirit += spirit + random_values[4]

  def _update_vars(self):
    self._max_age = max(self._age, self._max_age)
    self._max_charm = max(self._charm, self._max_charm)
    self._max_intelligence = max(self._intelligence, self._max_intelligence)
    self._max_strength = max(self._strength, self._max_strength)
    self._max_money = max(self._money, self._max_money)
    self._max_spirit = max(self._spirit, self._max_spirit)
    self._min_charm = min(self._charm, self._min_charm)
    self._min_intelligence = min(self._intelligence, self._min_intelligence)
    self._min_strength = min(self._strength, self._min_strength)
    self._min_money = min(self._money, self._min_money)
    self._min_spirit = min(self._spirit, self._min_spirit)
    self._condition_vars.update({
      "AGE": self._age,
      "CHR": self._charm,
      "INT": self._intelligence,
      "STR": self._strength,
      "MNY": self._money,
      "SPR": self._spirit,
      "HAGE": self._max_age,
      "HCHR": self._max_charm,
      "HINT": self._max_intelligence,
      "HSTR": self._max_strength,
      "HMNY": self._max_money,
      "HSPR": self._max_spirit,
      "LCHR": self._min_charm,
      "LINT": self._min_intelligence,
      "LSTR": self._min_strength,
      "LMNY": self._min_money,
      "LSPR": self._min_spirit,
    })

  def end(self) -> End:
    overall = sum([
      self._max_charm,
      self._max_intelligence,
      self._max_strength,
      self._max_money,
      self._max_spirit
    ]) * 2 + self._max_age // 2
    self.statistics.finished_games += 1
    self._condition_vars["SUM"] = overall
    self._condition_vars["TMS"] = self.statistics.finished_games
    return End(
      self._raw_talents,
      self._check_achievements(Opportunity.END),
      self._max_age,
      self._max_charm,
      self._max_intelligence,
      self._max_strength,
      self._max_money,
      self._max_spirit,
      overall,
      self.judge(self._max_age, self.config.stat.rarity.age),
      self.judge(self._max_charm, self.config.stat.rarity.charm),
      self.judge(self._max_intelligence, self.config.stat.rarity.intelligence),
      self.judge(self._max_strength, self.config.stat.rarity.strength),
      self.judge(self._max_money, self.config.stat.rarity.money),
      self.judge(self._max_spirit, self.config.stat.rarity.spirit),
      self.judge(overall, self.config.stat.rarity.overall))

  @staticmethod
  def judge(value: int, standard: list[StatRarityItem]) -> StatRarityItem:
    for i in reversed(standard):
      if value > i.min:
        return i
    return standard[0]

  def create_character(
    self, seed: int | None = None, name: str = "独一无二的我"
  ) -> GeneratedCharacter:
    random = Random()
    if seed is None:
      seed = int.from_bytes(random.randbytes(4), "little")
    random.seed(seed)
    choices, weights = zip(*self.config.character.talent_count_weight.items())
    talent_count = random.choices(choices, weights)[0]
    talents = random.sample(
      [id for id, talent in TALENT.items() if not talent.exclusive], talent_count)
    choices, weights = zip(*self.config.character.stat_value_weight.items())
    charm, intelligence, strength, money = random.choices(choices, weights, k=4)
    self.statistics.character = GeneratedCharacter(
      -1, name, talents, charm, intelligence, strength, money, seed)
    return self.statistics.character

  def set_character(self, character: Character) -> tuple[list[Talent], list[Talent]]:
    talents = [TALENT[id] for id in character.talents]
    real_talents = self.set_talents(talents)
    self.set_stats(character.charm, character.intelligence, character.strength, character.money)
    return talents, real_talents
