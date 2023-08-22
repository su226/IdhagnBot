from argparse import Namespace
from typing import List, Tuple

import cv2
import numpy as np
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

COEFFICENTS = [0.01, 0.03, 0.05, 0.08, 0.12, 0.17, 0.23, 0.3, 0.4, 0.6]
BORDERS = [25, 52, 67, 83, 97, 108, 118, 128, 138, 148]


DistortCoefficents = Tuple[float, float, float, float]
def distort(im: Image.Image, coefficients: DistortCoefficents) -> Image.Image:
  res = cv2.undistort(
    np.asarray(im),
    np.array([[100, 0, im.width / 2], [0, 100, im.height / 2], [0, 0, 1]]),
    np.asarray(coefficients)
  )
  return Image.fromarray(np.array(res, dtype=np.uint8))


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式"
)
matcher = (
  command.CommandBuilder("meme_pic.fisheye", "鱼眼")
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
    target = target.resize((500, 500), imutil.scale_resample())
    frames: List[Image.Image] = [target]
    for coefficent, border in zip(COEFFICENTS, BORDERS):
      frame = distort(target, (coefficent, 0, 0, 0))
      frame = frame.crop((border, border, 499 - border, 499 - border))
      frames.append(frame.resize((500, 500), imutil.scale_resample()))
    frames.extend(frames[::-1])
    return imutil.to_segment(frames, 50, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
