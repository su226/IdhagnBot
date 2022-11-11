import random
from typing import Literal, cast, get_args

from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
from pydantic import BaseModel

from util import command, configs, misc


class Config(BaseModel):
  front_weight: float = 49.5
  back_weight: float = 49.5
  stand_weight: float = 1
  limit: int = 10000
  binomial_limit: int = 10 ** 15

  @property
  def fail_str(self) -> str:
    return USAGE_FAIL.format(self.binomial_limit, self.limit)


CONFIG = configs.SharedConfig("coin", Config)


USAGE_BASE = '''\
/硬币 - 抛出一枚硬币
/硬币 <硬币数量> - 抛出一把硬币'''
USAGE_FAIL = "硬币数量必须是不超过 {} 的正整数\n超过 {} 的硬币将会使用二项分布估算"
FlipResult = Literal["front", "back", "stand"]


def flip() -> FlipResult:
  config = CONFIG()
  result = random.choices(
    get_args(FlipResult), [config.front_weight, config.back_weight, config.stand_weight]
  )[0]
  return cast(FlipResult, result)


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
  config = CONFIG()
  stand = misc.binomial_sample(
    count, config.stand_weight / (config.front_weight + config.back_weight + config.stand_weight)
  )
  front = misc.binomial_sample(
    count - stand, config.front_weight / (config.front_weight + config.back_weight)
  )
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


coin = (
  command.CommandBuilder("coin", "硬币", "coin")
  .brief("试试你的运气")
  .usage(lambda: USAGE_BASE + "\n" + CONFIG().fail_str)
  .build()
)
@coin.handle()
async def handle_coin(arg: Message = CommandArg()):
  args = arg.extract_plain_text().strip()
  if len(args) == 0:
    await coin.finish(format_one())
  config = CONFIG()
  try:
    count = int(args)
  except ValueError:
    await coin.finish(config.fail_str)
  if count < 1 or count > config.binomial_limit:
    await coin.finish(config.fail_str)
  elif count == 1:
    await coin.finish(format_one())
  if count > config.limit:
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
