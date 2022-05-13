from argparse import Namespace
from io import BytesIO
import os

from PIL import Image, ImageOps, ImageDraw
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from util import resources
from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
COLOR = (78, 114, 184)

parser = ArgumentParser("/群青", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = nonebot.on_shell_command("群青", parser=parser)
matcher.__cmd__ = "群青"
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: Event, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  if errors:
    await matcher.finish("\n".join(errors))
  avatar = avatar.resize((500, 500), Image.ANTIALIAS).convert("LA")
  im = Image.new("L", (500, 500), 191)
  im.paste(avatar, mask=avatar.getchannel("A"))
  im = ImageOps.colorize(im, (0, 0, 0), (255, 255, 255), COLOR)
  draw = ImageDraw.Draw(im)
  font = resources.font("sans-bold", 80)
  draw.text((400, 50), "群", (255, 255, 255), font, stroke_width=2, stroke_fill=COLOR)
  draw.text((400, 150), "青", (255, 255, 255), font, stroke_width=2, stroke_fill=COLOR)
  font = resources.font("sans-bold", 40)
  draw.text((310, 270), "YOASOBI", (255, 255, 255), font, stroke_width=2, stroke_fill=COLOR)
  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
