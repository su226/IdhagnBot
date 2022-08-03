import os
import random
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, util

from ..util import get_image_and_user, segment_animated_image

plugin_dir = os.path.dirname(os.path.abspath(__file__))
BOXES = [
  [(32, 32, 108, 36)],
  [(32, 32, 122, 36)],
  [],
  [(123, 123, 19, 129)],
  [(185, 185, -50, 200), (33, 33, 289, 70)],
  [(32, 32, 280, 73)],
  [(35, 35, 259, 31)],
  [(175, 175, -50, 220)],
]

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "-rotate", "-旋转", type=float, metavar="角度", help="指定旋转角度而非随机")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "-webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.throw2", "扔2")
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
  avatar = avatar.rotate(
    random.uniform(0, 360) if args.rotate is None else args.rotate, util.resample)
  frames = []
  util.circle(avatar)
  for i in range(8):
    frame = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    for w, h, x, y in BOXES[i]:
      avatar1 = avatar.resize((w, h), util.scale_resample)
      frame.paste(avatar1, (x, y), mask=avatar1)
    frames.append(frame)
  await matcher.finish(segment_animated_image(args.format, frames, 100))
