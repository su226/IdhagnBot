from argparse import Namespace
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from ..util import segment_animated_image, get_image_and_user, circle

plugin_dir = os.path.dirname(os.path.abspath(__file__))
BOXES = [
  (14, 20, 98, 98),
  (12, 33, 101, 85),
  (8, 40, 110, 76),
  (10, 33, 102, 84),
  (12, 20, 98, 98)
]

parser = ArgumentParser("/petpet", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument("-circle", "-圆", action="store_true", help="让头像变圆")
group = parser.add_mutually_exclusive_group()
group.add_argument("-webp", action="store_const", dest="format", const="webp", default="gif", help="使用WebP而非GIF格式")
group.add_argument("-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = nonebot.on_shell_command("petpet", aliases={"pet", "rua"}, parser=parser)
matcher.__cmd__ = ["petpet", "pet", "rua"]
matcher.__brief__ = "rua~"
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: Event, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  if errors:
    await matcher.finish("\n".join(errors))
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
