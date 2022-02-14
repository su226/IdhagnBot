from ..typing.commons import WeightsList
from enum import IntEnum

class Rarity(IntEnum):
  COMMON    = 0 # 常见
  UNCOMMON  = 1 # 稀有
  RARE      = 2 # 罕见
  LEGENDARY = 3 # 传说

Weights = dict[int, float]
Age = dict[int, Weights]

def parse_weights(items: WeightsList) -> Weights:
  result = {}
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
