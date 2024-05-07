import heapq
import itertools
import random
import re
from typing import Callable, List

from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
from pydantic import BaseModel

from util import command, configs, misc


class Config(BaseModel):
  limit: int = 10000
  binomial_limit: int = 10 ** 15
  max_faces: int = 100
  max_display: int = 100
  max_lines: int = 10

  @property
  def fail_str(self) -> str:
    return USAGE_FAIL.format(self.binomial_limit, self.limit)


CONFIG = configs.SharedConfig("dice", Config)


USAGE_BASE = '''\
/骰子 - 扔出一个六面骰子
/骰子 <个数> - 扔出多个六面骰子
/骰子 d<面数> - 扔出一个多面骰子
/骰子 <个数>d<面数> - 扔出多个多面骰子'''
USAGE_FAIL = "骰子数量必须是不超过 {} 的正整数\n超过 {} 的骰子将会使用二项分布估算"
SPECIAL_NAMES = {
  1: "骰(dan)子(zhu)",
  2: "骰(ying)子(bi)",
}
DICE_RE = re.compile(r"^(\d+)?(?:d(\d+))?$")


def dice_simulation(count: int, faces: int) -> List[int]:
  results = [0 for _ in range(faces)]
  for _ in range(count):
    results[random.randrange(faces)] += 1
  return results


def dice_binomial(count: int, faces: int) -> List[int]:
  results = []
  for used in range(faces):
    current = misc.binomial_sample(count, 1.0 / (faces - used))
    results.append(current)
    count -= current
  return results


def format_dice(func: Callable[[int, int], List[int]], count: int, faces: int) -> str:
  config = CONFIG()
  raw_data = func(count, faces)
  message = f"你抛出了 {count} 个 {faces} 面{SPECIAL_NAMES.get(faces, '骰子')}，"
  sum_value = sum(face * count for face, count in enumerate(raw_data, 1))
  if count <= config.max_display:
    dices = itertools.chain.from_iterable([face] * count for face, count in enumerate(raw_data, 1))
    message += "点数分别是：" + "、".join([str(face) for face in dices])
  else:
    message += "最多的点数是：\n"
    data = heapq.nlargest(config.max_lines + 1, enumerate(raw_data, 1), key=lambda x: x[1])
    segments = [f"{number} 点 {count} 个" for number, count in data if count]
    if len(segments) > config.max_lines:
      segments = segments[:config.max_lines - 1]
      count -= sum(count for _, count in data[:config.max_lines])
      segments.append(f"其他 {count} 个")
    message += "\n".join(segments)
  message += f"\n总和为 {sum_value}"
  return message


def dice_usage() -> str:
  return USAGE_BASE + "\n" + CONFIG().fail_str
dice = (
  command.CommandBuilder("dice", "骰子", "色子", "dice")
  .brief("先过个sancheck")
  .usage(dice_usage)
  .build()
)
@dice.handle()
async def handle_dice(args: Message = CommandArg()):
  config = CONFIG()
  match = DICE_RE.match(str(args).rstrip())
  if match is None:
    await dice.finish(dice_usage())
  count = 1 if match[1] is None else int(match[1])
  if count < 1:
    await dice.finish("个数必须为正整数")
  elif count > config.binomial_limit:
    await dice.finish(config.fail_str)
  faces = 6 if match[2] is None else int(match[2])
  if faces < 1:
    await dice.finish("面数必须为正整数")
  elif faces > config.max_faces:
    await dice.finish(f"最多只能扔出 {config.max_faces} 面的骰子")
  if count == 1:
    await dice.finish((
      f"你扔出了一个 {faces} 面{SPECIAL_NAMES.get(faces, '骰子')}，{random.randint(1, faces)} 朝上"
    ))
  elif count > config.limit:
    await dice.finish(format_dice(dice_binomial, count, faces))
  else:
    await dice.finish(format_dice(dice_simulation, count, faces))
