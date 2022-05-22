from enum import IntEnum
from typing import Iterable, TypedDict


class Rarity(IntEnum):
  COMMON = 0  # 常见
  UNCOMMON = 1  # 稀有
  RARE = 2  # 罕见
  LEGENDARY = 3  # 传说


class EmptyDict(TypedDict):
  pass


Weights = dict[int, float]
Age = dict[int, Weights]


def parse_weights(items: Iterable[int | str]) -> Weights:
  result: Weights = {}
  for item in items:
    if isinstance(item, str):
      if "*" in item:
        id, weight = item.split("*")
        result[int(id)] = float(weight)
      else:
        result[int(item)] = 1
    else:
      result[item] = 1
  return result
