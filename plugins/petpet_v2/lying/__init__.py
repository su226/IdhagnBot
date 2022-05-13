from argparse import Namespace
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from ..util import segment_animated_image, get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
BOXES = [
  (39, 169, 267, 141), (40, 167, 264, 143), (38, 174, 270, 135),
  (40, 167, 264, 143), (38, 174, 270, 135), (40, 167, 264, 143),
  (38, 174, 270, 135), (40, 167, 264, 143), (38, 174, 270, 135),
  (28, 176, 293, 134), (5, 215, 333, 96), (10, 210, 321, 102),
  (3, 210, 330, 104), (4, 210, 328, 102), (4, 212, 328, 100),
  (4, 212, 328, 100), (4, 212, 328, 100), (4, 212, 328, 100),
  (4, 212, 328, 100), (29, 195, 285, 120)
]

parser = ArgumentParser("/趴", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument("-webp", action="store_const", dest="format", const="webp", default="gif", help="使用WebP而非GIF格式")
group.add_argument("-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = nonebot.on_shell_command("趴", parser=parser)
matcher.__cmd__ = ["趴"]
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
  for i in range(20):
    template = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    im = Image.new("RGB", template.size, (255, 255, 255))
    x, y, w, h = BOXES[i]
    avatar1 = avatar.resize((w, h), Image.ANTIALIAS)
    im.paste(avatar1, (x, y), avatar1)
    im.paste(template, mask=template)
    frames.append(im)
  await matcher.finish(segment_animated_image(args.format, frames, 80))
