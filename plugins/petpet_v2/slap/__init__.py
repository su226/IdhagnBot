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
SOURCE_BOXES = [(6, 18), (6, 18), (6, 18), (7, 18)]
TARGET_BOXES = [(40, 37), (41, 37), (45, 45), (44, 41)]

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "-source", default="", metavar="源", help="同上")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "-webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "-apng", "-png", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.slap", "打", "打脸")
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
    avatar2, _ = await get_image_and_user(bot, event, args.source, event.user_id)
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  avatar = avatar.resize((22, 22), Image.ANTIALIAS)
  avatar2 = avatar2.resize((30, 30), Image.ANTIALIAS)
  circle(avatar)
  circle(avatar2)
  frames: list[Image.Image] = []
  for i in range(4):
    frame = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    frame.paste(avatar, TARGET_BOXES[i], avatar)
    frame.paste(avatar2, SOURCE_BOXES[i], avatar2)
    frames.append(frame)
  await matcher.finish(segment_animated_image(args.format, frames, 50))
