from typing import List, TypedDict, Union

WeightsList = List[Union[int, str]]


class Age(TypedDict):
  age: Union[int, str]
  event: WeightsList
