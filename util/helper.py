import asyncio
import itertools
import random
from datetime import timedelta
from typing import Sequence, TypeVar

import nonebot
from nonebot.adapters.onebot.v11 import Message, MessageEvent

T = TypeVar("T")


def weighted_choice(choices: list[T | tuple[T, float]]) -> T:
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


def format_time(seconds: float | timedelta) -> str:
  if isinstance(seconds, timedelta):
    seconds = seconds.seconds
  seconds = round(seconds)
  minutes, seconds = divmod(seconds, 60)
  hours, minutes = divmod(minutes, 60)
  days, hours = divmod(hours, 24)
  segments = []
  if days:
    segments.append(f"{days} 天")
  if hours:
    segments.append(f"{hours} 时")
  if minutes:
    segments.append(f"{minutes} 分")
  if seconds:
    segments.append(f"{seconds} 秒")
  return " ".join(segments)


class AggregateError(Exception, Sequence[str]):
  def __init__(self, *errors: "str | AggregateError") -> None:
    super().__init__(*itertools.chain.from_iterable(
      error if isinstance(error, AggregateError) else [error]
      for error in errors))

  def __len__(self) -> int:
    return len(self.args)

  def __getitem__(self, index: int) -> str:
    return self.args[index]


def prompt(event: MessageEvent) -> asyncio.Future[Message]:
  async def check_prompt(event2: MessageEvent):
    return (
      event.user_id == event2.user_id
      and getattr(event, "group_id", -1) == getattr(event2, "group_id", -1))

  async def handle_prompt(event2: MessageEvent):
    future.set_result(event2.get_message())

  future = asyncio.get_event_loop().create_future()
  nonebot.on_message(check_prompt, handlers=[handle_prompt], temp=True, priority=-1)
  return future
