from argparse import Namespace
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot.params import ShellCommandArgs

from util import command
from util.helper import notnone
from ..util import segment_animated_image, get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
BOXES = [
  (39, 40), (39, 40), (39, 40), (39, 30), (39, 30), (39, 32), (39, 32),
  (39, 32), (39, 32), (39, 32), (39, 32), (39, 32), (39, 32), (39, 32),
  (39, 32), (39, 30), (39, 27), (39, 32), (37, 49), (37, 64), (37, 67),
  (37, 67), (39, 69), (37, 70), (37, 70)
]

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument("-webp", action="store_const", dest="format", const="webp", default="gif", help="使用WebP而非GIF格式")
group.add_argument("-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (command.CommandBuilder("petpet_v2.trash", "垃圾", "trash")
  .category("petpet_v2")
  .shell(parser)
  .build())
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  if errors:
    await matcher.finish("\n".join(errors))
  avatar = notnone(avatar).resize((79, 79), Image.ANTIALIAS)
  frames: list[Image.Image] = []
  for i in range(25):
    template = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    im = Image.new("RGB", template.size, (255, 255, 255, 0))
    im.paste(avatar, BOXES[i], avatar)
    im.paste(template, mask=template)
    frames.append(im)
  await matcher.finish(segment_animated_image(args.format, frames, 40))
