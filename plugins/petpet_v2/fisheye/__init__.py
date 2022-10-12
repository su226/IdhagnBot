from argparse import Namespace

import cv2
import numpy as np
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, util

from ..util import get_image_and_user, segment_animated_image

DistortCoefficents = tuple[float, float, float, float]


def distort(im: Image.Image, coefficients: DistortCoefficents) -> Image.Image:
  res = cv2.undistort(
    np.asarray(im),
    np.array([[100, 0, im.width / 2], [0, 100, im.height / 2], [0, 0, 1]]),
    np.asarray(coefficients))
  return Image.fromarray(np.array(res, dtype=np.uint8))


COEFFICENTS = [0.01, 0.03, 0.05, 0.08, 0.12, 0.17, 0.23, 0.3, 0.4, 0.6]
BORDERS = [25, 52, 67, 83, 97, 108, 118, 128, 138, 148]
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
  command.CommandBuilder("petpet_v2.fisheye", "鱼眼")
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

  avatar = avatar.resize((500, 500), util.scale_resample)
  frames: list[Image.Image] = [avatar]
  for coefficent, border in zip(COEFFICENTS, BORDERS):
    frame = distort(avatar, (coefficent, 0, 0, 0))
    frame = frame.crop((border, border, 499 - border, 499 - border))
    frames.append(frame.resize((500, 500), util.scale_resample))
  frames.extend(frames[::-1])

  await matcher.finish(segment_animated_image(args.format, frames, 50))
