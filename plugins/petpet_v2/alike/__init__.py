import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw

from util import command, helper, resources

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
  except helper.AggregateError as e:
    await matcher.finish("\n".join(e))
  font = resources.font("sans", 24)
  w1, _ = font.getsize("你怎么跟")
  w2, _ = font.getsize("一样")
  im = Image.new("RGB", (w1 + w2 + 120, 110), (255, 255, 255))
  draw = ImageDraw.Draw(im)
  draw.text((10, 55), "你怎么跟", (0, 0, 0), font, "lm")
  draw.text((w1 + 110, 55), "一样", (0, 0, 0), font, "lm")
  avatar = avatar.resize((90, 90), Image.ANTIALIAS)
  im.paste(avatar, (w1 + 15, 10), avatar)
  f = BytesIO()
  im.save(f, "png")
  await matcher.finish(MessageSegment.image(f))
