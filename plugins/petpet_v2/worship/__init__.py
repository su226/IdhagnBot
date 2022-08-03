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
# pylama: skip=1
# RemapTransform((150, 150), ((0, -30), (135, 17), (135, 145), (0, 140)))
OLD_SIZE = 150, 150
NEW_SIZE = 135, 145
TRANSFORM = (
  0.8366013071895618, 1.2128331252511345e-14, -3.561263629370086e-12, -0.3071895424836637,
  0.8823529411764716, 26.47058823529454, -0.0018300653594771486, 3.1736140776801494e-17)

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "-webp", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式")
group.add_argument(
  "-apng", "-png", action="store_const", dest="format", const="png", help="使用APNG而非GIF格式")
matcher = (
  command.CommandBuilder("petpet_v2.worship", "膜拜")
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
  frames: list[Image.Image] = []
  avatar = avatar.resize(OLD_SIZE, util.scale_resample).transform(
    NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, resample=util.resample)
  for i in range(10):
    template = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    im = Image.new("RGB", template.size, (255, 255, 255))
    im.paste(avatar, mask=avatar)
    im.paste(template, mask=template)
    frames.append(im)
  await matcher.finish(segment_animated_image(args.format, frames, 40))
