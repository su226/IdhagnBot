import random
from argparse import Namespace
from pathlib import Path
from typing import List, Tuple, TypeVar, cast

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent
AVATAR_BOX = (0, 0, 360, 360)
PRICE_BOX = (225, 66, 305, 146)
SLIDE_FRAMES = 3
SLIDE_DURATION = 150
AVATAR_DURATION = 150
SCALE_FRAMES = 3
SCALE_DURATION = 150
PRICE_FRAMES = 5
PRICE_DURATION = 250


T = TypeVar("T", bound=Tuple[float, ...])
def lerp(box1: T, box2: T, r2: float) -> T:
  r1 = 1 - r2
  return cast(T, tuple(int(i * r1 + j * r2) for i, j in zip(box1, box2)))


def paste(im: Image.Image, im2: Image.Image, box: Tuple[int, int, int, int]) -> None:
  im2 = im2.resize((box[2] - box[0], box[3] - box[1]), imutil.scale_resample())
  im.paste(im2, box, im2)


def make_price_im(bg: Image.Image, fg: Image.Image) -> Image.Image:
  im = bg.copy()
  im.paste(fg, (24 + random.randint(-10, 10), 93 + random.randint(-10, 10)))
  return im


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
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
  command.CommandBuilder("memes.indihome", "indihome", "印尼宽带", "印尼", "宽带")
  .category("memes")
  .brief("叮~")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    target = target.resize((360, 360), imutil.scale_resample())
    imutil.circle(target)
    frames: List[Image.Image] = []
    durations: List[int] = []
    for i in range(SLIDE_FRAMES):
      im = Image.new("RGB", (360, 360), (255, 255, 255))
      im.paste(target, lerp((360, 0), (0, 0), i / SLIDE_FRAMES), target)
      frames.append(im)
      durations.append(SLIDE_DURATION // SLIDE_FRAMES)
    avatar_im = Image.new("RGBA", (360, 360), (255, 255, 255, 255))
    avatar_im.paste(target, AVATAR_BOX, target)
    frames.append(avatar_im)
    durations.append(AVATAR_DURATION)
    white = Image.new("RGB", (360, 360), (255, 255, 255))
    price_bg_im = Image.open(DIR / "template.png")
    price_fg_im = Image.open(DIR / "text.png")
    for i in range(SCALE_FRAMES):
      ratio = (i + 1) / (SCALE_FRAMES + 1)
      price_im = make_price_im(price_bg_im, price_fg_im)
      im = Image.blend(white, price_im, ratio)
      paste(im, target, lerp(AVATAR_BOX, PRICE_BOX, ratio))
      frames.append(im)
      durations.append(SCALE_DURATION // SCALE_FRAMES)
    for i in range(PRICE_FRAMES):
      price_im = make_price_im(price_bg_im, price_fg_im)
      paste(price_im, target, PRICE_BOX)
      frames.append(price_im)
      durations.append(PRICE_DURATION // PRICE_FRAMES)
    return imutil.to_segment(frames, durations, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
