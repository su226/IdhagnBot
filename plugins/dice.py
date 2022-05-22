import heapq
import random
import re
from typing import Callable

import numpy
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg

from util import command

CONFIG = {
  "limit": 10000,
  "binomial_limit": 10 ** 15,
  "faces": 100,
  "max_lines": 10,
}


def dice_simulation(count: int, faces: int) -> list[int]:
  results = [0 for _ in range(faces)]
  for _ in range(count):
    results[random.randrange(faces)] += 1
  return results


def dice_binomial(count: int, faces: int) -> list[int]:
  results = []
  for used in range(faces):
    current = numpy.random.binomial(count, 1.0 / (faces - used))
    results.append(current)
    count -= current
  return results


def format_dice(func: Callable[[int, int], list[int]], count: int, faces: int) -> str:
  raw_data = func(count, faces)
  data = list(filter(lambda x: x[1], heapq.nlargest(
    CONFIG["max_lines"] + 1, enumerate(raw_data, 1), key=lambda x: x[1])))
  sum_value = sum(face * count for face, count in enumerate(raw_data, 1))
  segments = [f"{number}: {count}" for number, count in data]
  if len(segments) > CONFIG["max_lines"]:
    segments = segments[:CONFIG["max_lines"] - 1]
    segments.append("……")
  return (
    f"你抛出了 {count} 个 {faces} 面{SPECIAL_NAMES.get(faces, '骰子')}，结果如下：\n"
    + "\n".join(segments) + f"\n总和为 {sum_value}")


SPECIAL_NAMES = {
  1: "骰(dan)子(zhu)",
  2: "骰(ying)子(bi)"
}
DICE_RE = re.compile(r"^(\d+)?(?:d(\d+))?$")

USAGE = '''\
/骰子 - 扔出一个六面骰子
/骰子 <个数> - 扔出多个六面骰子
/骰子 d<面数> - 扔出一个多面骰子
/骰子 <个数>d<面数> - 扔出多个多面骰子'''
dice = (
  command.CommandBuilder("dice", "骰子", "色子", "dice")
  .brief("先过个sancheck")
  .usage(USAGE)
  .build())


@dice.handle()
async def handle_dice(args: Message = CommandArg()):
  match = DICE_RE.match(str(args).rstrip())
  if match is None:
    await dice.finish(USAGE)
  count = 1 if match[1] is None else int(match[1])
  if count < 1:
    await dice.finish("个数必须为正整数")
  elif count > CONFIG["binomial_limit"]:
    await dice.finish(f"最多只能扔出 {CONFIG['binomial_limit']} 个骰子")
  faces = 6 if match[2] is None else int(match[2])
  if faces < 1:
    await dice.finish("面数必须为正整数")
  elif faces > CONFIG["faces"]:
    await dice.finish(f"最多只能扔出 {CONFIG['faces']} 面的骰子")
  if count == 1:
    await dice.send(
      f"你扔出了一个 {faces} 面{SPECIAL_NAMES.get(faces, '骰子')}，{random.randint(1, faces)} 朝上")
  elif count > CONFIG["limit"]:
    await dice.finish(format_dice(dice_binomial, count, faces))
  else:
    await dice.finish(format_dice(dice_simulation, count, faces))
