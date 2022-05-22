from typing import TypedDict

WeightsList = list[int | str]


class Age(TypedDict):
  age: int | str
  event: WeightsList
