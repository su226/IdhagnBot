import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, util

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
# pylama:skip=1
# RemapTransform((450, 450), ((15, 11), (448, 0), (445, 452), (0, 461)))
OLD_SIZE = 450, 450
NEW_SIZE = 448, 461
TRANSFORM = (
  1.0462493084523434, 0.03487497694841008, -16.077364373214344, 0.026154227716037853,
  1.029525509185637, -11.717094016783891, 1.3106774868236476e-05, 6.215553491345412e-05)

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (
  command.CommandBuilder("petpet_v2.cover", "捂脸")
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
  im = Image.new("RGB", template.size, (255, 255, 255))
  avatar = avatar.resize(OLD_SIZE, util.scale_resample).transform(
    NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, util.resample)
  im.paste(avatar, (120, 154), avatar)
  im.paste(template, mask=template)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
