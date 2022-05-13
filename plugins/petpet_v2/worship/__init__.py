from argparse import Namespace
import os

from PIL import Image
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.rule import ArgumentParser, ParserExit
from nonebot.params import ShellCommandArgs
import nonebot

from ..util import segment_animated_image, get_image_and_user, RemapTransform

plugin_dir = os.path.dirname(os.path.abspath(__file__))
TRANSFORM = RemapTransform((150, 150), ((0, -30), (135, 17), (135, 145), (0, 140)))

parser = ArgumentParser("/膜拜", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument("-webp", action="store_const", dest="format", const="webp", default="gif", help="使用WebP而非GIF格式")
group.add_argument("-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = nonebot.on_shell_command("膜拜", parser=parser)
matcher.__cmd__ = ["膜拜"]
matcher.__doc__ = parser.format_help()
matcher.__cat__ = "petpet_v2"
@matcher.handle()
async def handler(bot: Bot, event: Event, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  if errors:
    await matcher.finish("\n".join(errors))
  frames: list[Image.Image] = []
  avatar = avatar.resize(TRANSFORM.old_size, Image.ANTIALIAS).transform(TRANSFORM.new_size, TRANSFORM, resample=Image.BICUBIC)
  for i in range(10):
    template = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    im = Image.new("RGB", template.size, (255, 255, 255))
    im.paste(avatar, mask=avatar)
    im.paste(template, mask=template)
    frames.append(im)
  await matcher.finish(segment_animated_image(args.format, frames, 40))
