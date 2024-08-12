import math
import random
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.misc import range_int
from util.user_aliases import AvatarGetter, DefaultType

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--duration", "-d", type=range_int(1, 200), default=50, metavar="毫秒", help=(
  "[1, 200]之间的整数，默认为50"
))
parser.add_argument("--original", "-o", action="store_true", help=(
  "使用原图，可能出现文件过大发送失败"
))
group = parser.add_mutually_exclusive_group()
group.add_argument("--clockwise", "-c", dest="acw", action="store_false", default=None, help=(
  "始终使用顺时针而非随机"
))
group.add_argument("--anticlockwise", "-a", dest="acw", action="store_true", help=(
  "始终使用逆时针而非随机"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式",
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式",
)
matcher = (
  command.CommandBuilder("meme_pic.windmill", "风车转")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    acw = bool(random.randrange(2)) if args.acw is None else args.acw
    if not args.original and target.width > 300:
      target = target.resize((300, 300), imutil.scale_resample())
    base = Image.new("RGB", (target.width * 2, target.height * 2))
    base.paste(target)
    base.paste(target.transpose(Image.Transpose.ROTATE_90), (0, target.height))
    base.paste(target.transpose(Image.Transpose.ROTATE_180), (target.width, target.height))
    base.paste(target.transpose(Image.Transpose.ROTATE_270), (target.width, 0))
    w = int(base.width / math.sqrt(2))
    x = (base.width - w) // 2
    y = (base.height - w) // 2
    crop = (x, y, x + w, y + w)
    frames = [
      base.rotate(i if acw else -i, imutil.resample()).crop(crop)
      for i in range(0, 90, 18)
    ]
    return imutil.to_segment(frames, args.duration, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
