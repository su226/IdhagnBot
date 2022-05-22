import os
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, helper

from ..util import circle, get_image_and_user, segment_animated_image

plugin_dir = os.path.dirname(os.path.abspath(__file__))
BOXES = [
  (14, 20, 98, 98), (12, 33, 101, 85), (8, 40, 110, 76), (10, 33, 102, 84), (12, 20, 98, 98)]

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument("-circle", "-圆", action="store_true", help="让头像变圆")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "-webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.petpet", "petpet", "pet", "rua")
  .brief("rua~")
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
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  frames: list[Image.Image] = []
  for i in range(5):
    frame = Image.new('RGBA', (112, 112))
    x, y, w, h = BOXES[i]
    resized = avatar.resize((w, h), Image.ANTIALIAS)
    if args.circle:
      circle(resized, args.format != "gif")
    frame.paste(resized, (x, y), resized)
    hand = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    frame.paste(hand, mask=hand)
    frames.append(frame)
  await matcher.finish(segment_animated_image(args.format, frames, 60))
