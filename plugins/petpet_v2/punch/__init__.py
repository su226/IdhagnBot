from argparse import Namespace
import os

from PIL import Image, ImageOps
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from ..util import get_image_and_user, segment_animated_image

plugin_dir = os.path.dirname(os.path.abspath(__file__))
BOXES = [
  (-50, 20), (-40, 10), (-30, 0), (-20, -10), (-10, -10), (0, 0), (10, 10),
  (20, 20), (10, 10), (0, 0), (-10, -10), (10, 0), (-30, 10)
]

parser = ArgumentParser("/打拳", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument("-webp", action="store_const", dest="format", const="webp", default="gif", help="使用WebP而非GIF格式")
group.add_argument("-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = nonebot.on_shell_command("打拳", parser=parser)
matcher.__cmd__ = "打拳"
matcher.__brief__ = "现实中我唯唯诺诺，网络上我重拳出击"
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: Event, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  if errors:
    await matcher.finish("\n".join(errors))
  img = ImageOps.fit(avatar, (260, 230), Image.ANTIALIAS)
  frames: list[Image.Image] = []
  for i in range(13):
    frame = Image.new("RGBA", (260, 230))
    frame.paste(img, BOXES[i])
    template = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    frame.paste(template, mask=template)
    frames.append(frame)
  await matcher.finish(segment_animated_image(args.format, frames, 30))
