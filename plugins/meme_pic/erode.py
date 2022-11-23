import math
from argparse import Namespace
from typing import List

import cv2
import numpy as np
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil, misc
from util.misc import range_float
from util.user_aliases import AvatarGetter


def get_kernel(x: float, y: float) -> np.ndarray:
  assert x >= 0 and y >= 0
  arr = np.ones((math.ceil(y * 2 + 1), math.ceil(x * 2 + 1)))
  if (m := x % 1) > 0:
    arr[:, 0] *= m
    arr[:, -1] *= m
  if (m := y % 1) > 0:
    arr[0, :] *= m
    arr[-1, :] *= m
  return arr


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("-x", type=range_float(0), default=2, metavar="半径", help=(
  "水平半径，必须是大于等于 0 的小数，默认为 2"
))
parser.add_argument("-y", type=range_float(0), default=0, metavar="半径", help=(
  "垂直半径，必须是大于等于 0 的小数，默认为 0"
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


erode = (
  command.CommandBuilder("meme_pic.erode", "腐蚀")
  .category("meme_pic")
  .brief("[动]")
  .shell(parser)
  .build()
)
@erode.handle()
async def handle_erode(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, raw=True)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    kernel = get_kernel(args.x, args.y)

    frames: List[Image.Image] = []
    for raw in imutil.frames(target):
      frame = ImageOps.contain(raw.convert("RGBA"), (720, 720), imutil.scale_resample())
      frame = np.array(frame)
      frame = cv2.erode(frame, kernel)
      frame = Image.fromarray(frame, "RGBA")
      frames.append(frame)

    return imutil.to_segment(frames, target, afmt=args.format)

  await erode.finish(await misc.to_thread(make))


dilate = (
  command.CommandBuilder("meme_pic.dilate", "膨胀")
  .category("meme_pic")
  .brief("[动]")
  .shell(parser)
  .build()
)
@dilate.handle()
async def handle_dilate(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, raw=True)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    kernel = get_kernel(args.x, args.y)

    frames: List[Image.Image] = []
    for raw in imutil.frames(target):
      frame = ImageOps.contain(raw.convert("RGBA"), (720, 720), imutil.scale_resample())
      frame = np.array(frame)
      frame = cv2.dilate(frame, kernel)
      frame = Image.fromarray(frame, "RGBA")
      frames.append(frame)

    return imutil.to_segment(frames, target, afmt=args.format)

  await dilate.finish(await misc.to_thread(make))
