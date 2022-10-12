from argparse import Namespace
from io import BytesIO
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageChops, ImageEnhance, ImageMath, ImageOps

from util import command, util

from ..util import get_image_and_user

plugin_dir = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="里图", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument(
  "--source", "-s", default="", metavar="表图", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument("--color", "-c", action="store_true", help="制作彩色幻影坦克")

matcher = (
  command.CommandBuilder("petpet_v2.miragetank", "幻影坦克", "tank")
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
    white, _ = await get_image_and_user(bot, event, args.source, event.user_id, raw=True)
    black, _ = await get_image_and_user(bot, event, args.target, event.self_id, raw=True)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  mode = "RGB" if args.color else "L"
  white = white.convert(mode)
  black = black.convert(mode)

  black = ImageOps.pad(black, white.size, util.scale_resample)

  if args.color:
    white = ImageEnhance.Color(white).enhance(0.5)
    black = ImageEnhance.Color(black).enhance(0.7)
    black = ImageEnhance.Brightness(black).enhance(0.18)

    a = ImageChops.subtract(black, white, offset=255).convert("L")
    r2, g2, b2 = black.split()
    r2 = ImageMath.eval("convert(l * 255 / a, 'L')", l=r2, a=a)
    g2 = ImageMath.eval("convert(l * 255 / a, 'L')", l=g2, a=a)
    b2 = ImageMath.eval("convert(l * 255 / a, 'L')", l=b2, a=a)
    im = Image.merge("RGBA", (r2, g2, b2, a))
  else:
    black = ImageEnhance.Brightness(black).enhance(0.3)

    a = ImageChops.subtract(black, white, offset=255)
    l = ImageMath.eval("convert(l * 255 / a, 'L')", l=black, a=a)
    im = Image.merge("LA", (l, a))

  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
