from argparse import Namespace
from io import BytesIO
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser("/注意力涣散", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = nonebot.on_shell_command("注意力涣散", aliases={"distracted"}, parser=parser)
matcher.__cmd__ = ["注意力涣散", "distracted"]
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: Event, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id, crop=False)
  if errors:
    await matcher.finish("\n".join(errors))

  im = avatar.resize((500, 500), Image.ANTIALIAS)
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im.paste(template, mask=template)

  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
