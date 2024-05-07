import random
from argparse import Namespace
from typing import List

import cv2
import numpy as np
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType


def motion_blur(im: Image.Image, angle: float, level: int) -> Image.Image:
  matrix = cv2.getRotationMatrix2D((level / 2, level / 2), angle + 45, 1)
  kernel = np.diag(np.ones(level))
  kernel = cv2.warpAffine(kernel, matrix, (level, level)) / level
  blurred = cv2.filter2D(np.asarray(im), -1, kernel)
  cv2.normalize(blurred, blurred, 0, 255, cv2.NORM_MINMAX)
  return Image.fromarray(np.array(blurred, dtype=np.uint8))


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式",
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式",
)
matcher = (
  command.CommandBuilder("meme_pic.shock", "震惊")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    target = target.resize((300, 300), imutil.scale_resample())
    frames: List[Image.Image] = []
    for _ in range(30):
      frames.append(
        motion_blur(target, random.randint(-90, 90), random.randint(1, 50))
        .rotate(random.randint(-20, 20), imutil.resample()),
      )
    return imutil.to_segment(frames, 10, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
