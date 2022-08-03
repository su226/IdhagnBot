import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, util

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
# pylama: skip=1
# RemapTransform((220, 160), ((0, 39), (225, 0), (236, 145), (25, 197)))
OLD_SIZE = 220, 160
NEW_SIZE = 236, 197
TRANSFORM = (
  0.8469606952031231, -0.13401276822833844, 5.226497960904075, 0.15932974592085844,
  0.9192100726203283, -35.84919283219329, -0.0004890372852200551, -0.00027999415409538726)

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (
  command.CommandBuilder("petpet_v2.laptop", "笔记本", "游戏")
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
  template = Image.open(os.path.join(plugin_dir, "template.png"))
  im = Image.new("RGB", template.size, (0, 0, 0))
  avatar = ImageOps.pad(avatar, OLD_SIZE, util.scale_resample).transform(
    NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, resample=util.resample)
  im.paste(avatar, (162, 119), avatar)
  im.paste(template, mask=template)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
