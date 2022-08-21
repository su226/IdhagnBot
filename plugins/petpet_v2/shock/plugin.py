from argparse import Namespace
import random

import cv2
import numpy as np
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, util

from ..util import get_image_and_user, segment_animated_image


def motion_blur(im: Image.Image, angle: float, level: int) -> Image.Image:
  matrix = cv2.getRotationMatrix2D((level / 2, level / 2), angle + 45, 1)
  kernel = np.diag(np.ones(level))
  kernel = cv2.warpAffine(kernel, matrix, (level, level)) / level
  blurred = cv2.filter2D(np.asarray(im), -1, kernel)
  cv2.normalize(blurred, blurred, 0, 255, cv2.NORM_MINMAX)
  return Image.fromarray(np.array(blurred, dtype=np.uint8))


parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.shock", "震惊")
  .category("petpet_v2")
  .shell(parser)
  .build())


@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  avatar = avatar.resize((300, 300), util.scale_resample)
  frames: list[Image.Image] = []
  for _ in range(30):
    frames.append(motion_blur(avatar, random.randint(-90, 90), random.randint(0, 50))
      .rotate(random.randint(-20, 20), util.resample))

  await matcher.finish(segment_animated_image(args.format, frames, 10))
