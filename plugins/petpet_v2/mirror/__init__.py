import math
import random
from argparse import Namespace
from io import BytesIO
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, util

from ..util import get_image_and_user

plugin_dir = Path(__file__).resolve().parent
DIRECTIONS = ["top", "bottom", "left", "right", "t", "b", "l", "r"]

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "--direction", "-d", choices=DIRECTIONS, help="镜像方向")
matcher = (
  command.CommandBuilder("petpet_v2.mirror", "镜像")
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
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id, crop=False)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  direction = args.direction
  if not direction:
    direction = random.choice(DIRECTIONS)

  match direction:
    case "top" | "t":
      flipped = avatar.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
      y = math.ceil(avatar.height / 2)
      avatar.paste(flipped.crop((0, y, avatar.width - 1, avatar.height - 1)), (0, y))
    case "bottom" | "b":
      flipped = avatar.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
      avatar.paste(flipped.crop((0, 0, avatar.width - 1, avatar.height // 2 - 1)))
    case "left" | "l":
      flipped = avatar.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
      x = math.ceil(avatar.width / 2)
      avatar.paste(flipped.crop((x, 0, avatar.width - 1, avatar.height - 1)), (x, 0))
    case "right" | "r":
      flipped = avatar.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
      avatar.paste(flipped.crop((0, 0, avatar.width // 2 - 1, avatar.height - 1)))

  f = BytesIO()
  avatar.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
