from argparse import Namespace
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot.params import ShellCommandArgs

from util import command, helper
from ..util import segment_animated_image, get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
BOXES = [
  (87, 77, 0), (96, 85, -45), (92, 79, -90), (92, 78, -135), (92, 75, -180),
  (92, 75, -225), (93, 76, -270), (90, 80, -315)
]

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument("-webp", action="store_const", dest="format", const="webp", default="gif", help="使用WebP而非GIF格式")
group.add_argument("-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (command.CommandBuilder("petpet_v2.roll", "滚雪球")
  .category("petpet_v2")
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
  frames: list[Image.Image] = []
  avatar = avatar.resize((210, 210), Image.ANTIALIAS)
  for i in range(8):
    template = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    im = Image.new("RGB", template.size, (255, 255, 255))
    x, y, deg = BOXES[i]
    avatar1 = avatar.rotate(deg, Image.BICUBIC)
    im.paste(avatar1, (x, y), avatar1)
    im.paste(template, mask=template)
    frames.append(im)
  await matcher.finish(segment_animated_image(args.format, frames, 100))
