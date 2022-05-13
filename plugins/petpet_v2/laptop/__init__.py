from argparse import Namespace
from io import BytesIO
import os

from PIL import Image, ImageOps
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from ..util import get_image_and_user, RemapTransform

plugin_dir = os.path.dirname(os.path.abspath(__file__))
TRANSFORM = RemapTransform((220, 160), ((0, 39), (225, 0), (236, 145), (25, 197)))

parser = ArgumentParser("/笔记本", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = nonebot.on_shell_command("笔记本", aliases={"游戏"}, parser=parser)
matcher.__cmd__ = ["笔记本", "游戏"]
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: Event, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id, crop=False)
  if errors:
    await matcher.finish("\n".join(errors))
  template = Image.open(os.path.join(plugin_dir, f"template.png"))
  im = Image.new("RGB", template.size, (0, 0, 0))
  avatar = ImageOps.pad(avatar, (220, 160), Image.ANTIALIAS).transform(TRANSFORM.new_size, TRANSFORM, resample=Image.BICUBIC)
  im.paste(avatar, (162, 119), avatar)
  im.paste(template, mask=template)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
