from argparse import Namespace
import os

from PIL import Image, ImageOps
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot.params import ShellCommandArgs

from util import command, helper
from ..util import get_image_and_user, segment_animated_image

plugin_dir = os.path.dirname(os.path.abspath(__file__))
BOXES = [
  (-50, 20), (-40, 10), (-30, 0), (-20, -10), (-10, -10), (0, 0), (10, 10),
  (20, 20), (10, 10), (0, 0), (-10, -10), (10, 0), (-30, 10)
]

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument("-webp", action="store_const", dest="format", const="webp", default="gif", help="使用WebP而非GIF格式")
group.add_argument("-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (command.CommandBuilder("petpet_v2.punch", "打拳")
  .category("petpet_v2")
  .brief("现实中我唯唯诺诺，网络上我重拳出击")
  .shell(parser)
  .build())
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  img = ImageOps.fit(avatar, (260, 230), Image.ANTIALIAS)
  frames: list[Image.Image] = []
  for i in range(13):
    frame = Image.new("RGBA", (260, 230))
    frame.paste(img, BOXES[i])
    template = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    frame.paste(template, mask=template)
    frames.append(frame)
  await matcher.finish(segment_animated_image(args.format, frames, 30))
