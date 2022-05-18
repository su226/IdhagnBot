import random
from typing import Literal

from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
import numpy

from util import command
from util.config import BaseConfig

class Config(BaseConfig):
  __file__ = "coin"
  front_weight: float = 49.5
  back_weight: float = 49.5
  stand_weight: float = 1
  limit: int = 10000
  binomial_limit: int = 10 ** 15

CONFIG = Config.load()

warn_str = f"超过 {CONFIG.limit} 的硬币将会使用二项分布估算"
fail_str = f"硬币数量必须是不超过 {CONFIG.binomial_limit} 的正整数\n{warn_str}"

def flip() -> Literal["front", "back", "stand"]:
  return random.choices(["front", "back", "stand"], [CONFIG.front_weight, CONFIG.back_weight, CONFIG.stand_weight])[0] # type: ignore

def flip_multiple(count) -> tuple[int, int, int]:
  front = 0
  back = 0
  stand = 0
  for _ in range(count):
    match flip():
      case "front":
        front += 1
      case "back":
        back += 1
      case "stand":
        stand += 1
  return front, back, stand

def flip_binomial(count: int) -> tuple[int, int, int]:
  stand = numpy.random.binomial(count, CONFIG.stand_weight / (CONFIG.front_weight + CONFIG.back_weight + CONFIG.stand_weight))
  front = numpy.random.binomial(count - stand, CONFIG.front_weight / (CONFIG.front_weight + CONFIG.back_weight))
  back = count - stand - front
  return front, back, stand

def format_one() -> str:
  match flip():
    case "front":
      return "你抛出了一枚硬币，正面朝上"
    case "back":
      return "你抛出了一枚硬币，反面朝上"
    case "stand":
      return "你抛出了一枚硬币，立起来了"

coin = (command.CommandBuilder("coin", "硬币", "coin")
  .brief("试试你的运气")
  .usage(f'''
/硬币 - 抛出一枚硬币
/硬币 <硬币数量> - 抛出一把硬币
{warn_str}''')
  .build())
@coin.handle()
async def handle_coin(arg: Message = CommandArg()):
  args = arg.extract_plain_text().strip()
  if len(args) == 0:
    await coin.finish(format_one())
  try:
    count = int(args)
  except ValueError:
    await coin.finish(fail_str)
  if count < 1 or count > CONFIG.binomial_limit:
    await coin.finish(fail_str)
  elif count == 1:
    await coin.finish(format_one())
  if count > CONFIG.limit:
    front, back, stand = flip_binomial(count)
  else:
    front, back, stand = flip_multiple(count)
  segments = [f"你抛出了 {count} 枚硬币"]
  if front > 0:
    segments.append(f"{front} 枚正面朝上")
  if back > 0:
    segments.append(f"{back} 枚反面朝上")
  if stand > 0:
    segments.append(f"{stand} 枚立起来了")
  await coin.finish("，".join(segments))
