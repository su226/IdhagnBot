from argparse import Namespace
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot.params import ShellCommandArgs

from util import command, helper
from ..util import circle, segment_animated_image, get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

OTHER_BOXES = [
  (58, 90), (62, 95), (42, 100), (50, 100), (56, 100), (18, 120), (28, 110),
  (54, 100), (46, 100), (60, 100), (35, 115), (20, 120), (40, 96)
]
SELF_BOXES = [
  (92, 64), (135, 40), (84, 105), (80, 110), (155, 82), (60, 96), (50, 80),
  (98, 55), (35, 65), (38, 100), (70, 80), (84, 65), (75, 65)
]

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument("-source", default="", metavar="源", help="同上")
group = parser.add_mutually_exclusive_group()
group.add_argument("-webp", action="store_const", dest="format", const="webp", default="gif", help="使用WebP而非GIF格式")
group.add_argument("-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (command.CommandBuilder("petpet_v2.kiss", "亲亲", "亲", "kiss")
  .category("petpet_v2")
  .shell(parser)
  .build())
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
    avatar2, _ = await get_image_and_user(bot, event, args.source, event.user_id)
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  circle(avatar)
  circle(avatar2)
  frames: list[Image.Image] = []
  avatar = avatar.resize((50, 50), Image.ANTIALIAS)
  avatar2 = avatar2.resize((40, 40), Image.ANTIALIAS)
  for i in range(13):
    frame = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    frame.paste(avatar, OTHER_BOXES[i], avatar)
    frame.paste(avatar2, SELF_BOXES[i], avatar2)
    frames.append(frame)
  await matcher.finish(segment_animated_image(args.format, frames, 50))
