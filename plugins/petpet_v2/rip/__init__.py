from argparse import Namespace
from io import BytesIO
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser("/撕", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument("-source", default="", metavar="源", help="也可使用\"滑稽\"或者\"熊猫头\"")
matcher = nonebot.on_shell_command("撕", parser=parser)
matcher.__cmd__ = ["撕"]
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  if args.source in ("huaji", "滑稽"):
    template = Image.open(os.path.join(plugin_dir, "template_huaji.png"))
  elif args.source in ("panda", "熊猫", "熊猫头"):
    template = Image.open(os.path.join(plugin_dir, "template_panda.png"))
  else:
    errors, avatar, _ = await get_image_and_user(bot, event, args.source, event.user_id)
    if errors:
      await matcher.finish("\n".join(errors))
    template = Image.new("RGBA", (1080, 804))
    avatar = avatar.resize((230, 230), Image.ANTIALIAS)
    template.paste(avatar, (408, 418), avatar)
    template2 = Image.open(os.path.join(plugin_dir, "template_custom.png"))
    template.paste(template2, mask=template2)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  if errors:
    await matcher.finish("\n".join(errors))
  avatar = avatar.resize((385, 385), Image.ANTIALIAS)
  im = Image.new("RGB", template.size, (255, 255, 255))
  left = avatar.rotate(24, Image.BICUBIC, True)
  im.paste(left, (-5, 355), left)
  right = avatar.rotate(-11, Image.BICUBIC, True)
  im.paste(right, (649, 310), right)
  im.paste(template, mask=template)
  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
