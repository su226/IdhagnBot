import math
import random
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIRECTIONS = ["top", "bottom", "left", "right", "t", "b", "l", "r"]


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--direction", "-d", choices=DIRECTIONS, help="镜像方向")
matcher = (
  command.CommandBuilder("meme_pic.mirror", "镜像")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET, crop=False)

  direction = args.direction
  if not direction:
    direction = random.choice(DIRECTIONS)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    if direction in ("top", "t"):
      flipped = target.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
      y = math.ceil(target.height / 2)
      target.paste(flipped.crop((0, y, target.width - 1, target.height - 1)), (0, y))
    elif direction in ("bottom", "b"):
      flipped = target.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
      target.paste(flipped.crop((0, 0, target.width - 1, target.height // 2 - 1)))
    elif direction in ("left", "l"):
      flipped = target.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
      x = math.ceil(target.width / 2)
      target.paste(flipped.crop((x, 0, target.width - 1, target.height - 1)), (x, 0))
    elif direction in ("right", "r"):
        flipped = target.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        target.paste(flipped.crop((0, 0, target.width // 2 - 1, target.height - 1)))
    return imutil.to_segment(target)

  await matcher.finish(await misc.to_thread(make))
