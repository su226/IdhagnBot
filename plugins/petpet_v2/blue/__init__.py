import os
from argparse import Namespace
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, text, util

from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
COLOR = (78, 114, 184)

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
matcher = (
  command.CommandBuilder("petpet_v2.blue", "群青")
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
  avatar = avatar.resize((500, 500), util.scale_resample).convert("LA")
  im = Image.new("L", (500, 500), 191)
  im.paste(avatar, mask=avatar.getchannel("A"))
  im = ImageOps.colorize(im, (0, 0, 0), (255, 255, 255), COLOR)  # type: ignore
  text.paste(
    im, (400, 50), "群", "sans bold", 80, color=(255, 255, 255), stroke=2, stroke_color=COLOR)
  text.paste(
    im, (400, 150), "青", "sans bold", 80, color=(255, 255, 255), stroke=2, stroke_color=COLOR)
  text.paste(
    im, (310, 270), "YOASOBI", "sans bold", 40, color=(255, 255, 255), stroke=2, stroke_color=COLOR)
  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
