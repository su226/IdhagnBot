import os
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, util

from ..util import get_image_and_user, segment_animated_image

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "-webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "-apng", "-png", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.tv", "电视")
  .category("petpet_v2")
  .shell(parser)
  .build())


@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  try:
    avatar, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))
  avatar = avatar.resize((235, 235), util.scale_resample)
  frames: list[Image.Image] = []
  for _ in range(4):
    for i in range(7):
      if i == 6:
        avatar = avatar.transpose(Image.Transpose.ROTATE_90)
      template = Image.open(os.path.join(plugin_dir, f"{i}.png"))
      im = Image.new("RGB", template.size, (36, 36, 56))
      im.paste(avatar, (254, 19), avatar)
      im.paste(template, mask=template)
      frames.append(im)
  await matcher.finish(segment_animated_image(args.format, frames, 50))