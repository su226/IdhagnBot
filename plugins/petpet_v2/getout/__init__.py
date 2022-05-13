from argparse import Namespace
from io import BytesIO
import os
import random

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from ..util import get_image_and_user, circle

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser("/爬", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument("-template", "-模板", type=int, metavar="编号", help="使用指定表情包而非随机，编号是[0, 91]之间的整数")
matcher = nonebot.on_shell_command("爬", aliases={"getout"}, parser=parser)
matcher.__cmd__ = ["爬", "getout"]
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: Event, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  if errors:
    await matcher.finish("\n".join(errors))
  template_id = random.randrange(92) if args.template is None else args.template
  if template_id < 0 or template_id > 91:
    await matcher.finish(f"模板编号需要是[0, 91]之间的整数")
  im = Image.open(os.path.join(plugin_dir, f"{template_id}.jpg"))
  avatar = avatar.resize((100, 100), Image.ANTIALIAS)
  circle(avatar)
  im.paste(avatar, (0, 400), avatar)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
