import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw, ImageOps

from util import command, helper, resources

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (
  command.CommandBuilder("petpet_v2.decent_kiss", "像样的亲亲")
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
  im = Image.new("RGB", (500, 500), (255, 255, 255))
  draw = ImageDraw.Draw(im)
  font = resources.font("sans-bold", 64)
  draw.text((250, 0), "很抱歉打扰你…", (0, 0, 0), font, "ma")
  avatar = ImageOps.fit(avatar, (500, 300), Image.ANTIALIAS)
  im.paste(avatar, (0, 100), avatar)
  font = resources.font("sans-bold", 32)
  draw.text((250, 400), "可是你今天甚至没有给我", (0, 0, 0), font, "ma")
  draw.text((250, 445), "一个像样的亲亲诶", (0, 0, 0), font, "ma")
  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
