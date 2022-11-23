from typing import List

from nonebot.adapters.onebot.v11 import Message

from . import Module


class StringModule(Module):
  def __init__(self, string: str) -> None:
    self.string = string

  async def format(self) -> List[Message]:
    return [Message(self.string)]
