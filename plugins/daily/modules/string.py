from nonebot.adapters.onebot.v11 import Message

from . import Module


class StringModule(Module):
  def __init__(self, string: str) -> None:
    self.string = string

  async def format(self) -> list[Message]:
    return [Message(self.string)]
