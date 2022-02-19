from typing import Awaitable, Callable, TypeVar
from core_plugins.context.typing import Context
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
import nonebot
import random

context: Context = nonebot.require("context")
exports = nonebot.export()

class Arguments(list[str]):
  def get(self, index: int, default: str = "") -> str:
    if index >= len(self):
      return default
    return self[index]

CallbackType = Callable[[Matcher, Arguments], Awaitable[None]]
@exports
def command(names: str | list[str], brief: str = "", usage: str | list[str] = "", contexts: int | list[int] = []) -> Callable[[CallbackType], CallbackType]:
  if not isinstance(names, list):
    names = [names]
  def decorator(func: CallbackType) -> CallbackType:
    async def handler(args = CommandArg()):
      await func(matcher, Arguments(str(args).split()))
    matcher = nonebot.on_command(names[0], context.in_context_rule(*contexts), set(names[1:]), handlers=[handler])
    matcher.__cmd__ = names
    matcher.__brief__ = brief
    matcher.__doc__ = usage
    matcher.__ctx__ = contexts
    return func
  return decorator

T = TypeVar("T")
@exports
def weighted_choice(choices: list[T | tuple[T, int]]) -> T:
  raw_choices = []
  weights = []
  for i in choices:
    if isinstance(i, tuple):
      raw_choices.append(i[0])
      weights.append(i[1])
    else:
      raw_choices.append(i)
      weights.append(1)
  return random.choices(raw_choices, weights)[0]
