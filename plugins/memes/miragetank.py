from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageChops, ImageEnhance, ImageMath, ImageOps

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="里图", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--source", "-s", default="", metavar="表图", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--color", "-c", action="store_true", help="保留里图颜色")
matcher = (
  command.CommandBuilder("memes.miragetank", "幻影坦克")
  .category("memes")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    black_task = g(args.target, DefaultType.TARGET, "里图", raw=True)
    white_task = g(args.source, DefaultType.SOURCE, "表图", raw=True)

  def make() -> MessageSegment:
    black, _ = black_task.result()
    white, _ = white_task.result()
    mode = "RGB" if args.color else "L"
    white = white.convert(mode)
    black = ImageOps.pad(black.convert(mode), white.size, imutil.scale_resample())

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

    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
