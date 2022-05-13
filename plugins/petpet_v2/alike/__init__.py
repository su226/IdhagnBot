from argparse import Namespace
from io import BytesIO
import os

from PIL import Image, ImageDraw
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from util import resources
from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser("/一样", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = nonebot.on_shell_command("一样", parser=parser)
matcher.__cmd__ = ["一样"]
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: Event, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  if errors:
    await matcher.finish("\n".join(errors))
  font = resources.font("sans", 24)
  w1, _ = font.getsize("你怎么跟")
  w2, _ = font.getsize("一样")
  im = Image.new("RGB", (w1 + w2 + 120, 110), (255, 255, 255))
  draw = ImageDraw.Draw(im)
  draw.text((10, 55), "你怎么跟", (0, 0, 0), font, "lm")
  draw.text((w1 + 110, 55), "一样", (0, 0, 0), font, "lm")
  avatar = avatar.resize((90, 90), Image.ANTIALIAS)
  im.paste(avatar, (w1 + 15, 10), avatar)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
