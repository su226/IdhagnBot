import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw

from util import command, text, util

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (
  command.CommandBuilder("petpet_v2.alike", "一样")
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
  left_im = text.render("你怎么跟", "sans", 24)
  right_im = text.render("一样", "sans", 24)
  im = Image.new("RGB", (left_im.width + right_im.width + 120, 110), (255, 255, 255))
  im.paste(left_im, (10, 55 - left_im.height // 2), left_im)
  im.paste(right_im, (left_im.width + 110, 55 - right_im.height // 2), right_im)
  avatar = avatar.resize((90, 90), util.scale_resample)
  im.paste(avatar, (left_im.width + 15, 10), avatar)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
