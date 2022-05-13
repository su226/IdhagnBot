from argparse import Namespace
from io import BytesIO
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from ..util import get_image_and_user, RemapTransform

plugin_dir = os.path.dirname(os.path.abspath(__file__))
TRANSFORM = RemapTransform((450, 450), ((15, 11), (448, 0), (445, 452), (0, 461)))

parser = ArgumentParser("/捂脸", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = nonebot.on_shell_command("捂脸", parser=parser)
matcher.__cmd__ = ["捂脸"]
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: Event, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  if errors:
    await matcher.finish("\n".join(errors))
  template = Image.open(os.path.join(plugin_dir, f"template.png"))
  im = Image.new("RGB", template.size, (255, 255, 255))
  avatar = avatar.resize(TRANSFORM.old_size, Image.ANTIALIAS).transform(TRANSFORM.new_size, TRANSFORM, resample=Image.BICUBIC)
  im.paste(avatar, (120, 154), avatar)
  im.paste(template, mask=template)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
