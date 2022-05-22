import os
import random
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, helper

from ..util import circle, get_image_and_user, segment_animated_image

plugin_dir = os.path.dirname(os.path.abspath(__file__))

AVATAR_BOX = (0, 0, 360, 360)
PRICE_BOX = (225, 66, 305, 146)
SLIDE_FRAMES = 3
SLIDE_DURATION = 150
AVATAR_DURATION = 150
SCALE_FRAMES = 3
SCALE_DURATION = 150
PRICE_FRAMES = 5
PRICE_DURATION = 250


def lerp(box1: tuple[int, ...], box2: tuple[int, ...], r2: float) -> tuple[int, ...]:
  r1 = 1 - r2
  return tuple(int(i * r1 + j * r2) for i, j in zip(box1, box2))


def paste(im: Image.Image, im2: Image.Image, box: tuple[int, int, int, int]):
  im2 = im2.resize((box[2] - box[0], box[3] - box[1]), Image.ANTIALIAS)
  im.paste(im2, box, im2)


def make_price_im(bg: Image.Image, fg: Image.Image) -> Image.Image:
  im = bg.copy()
  im.paste(fg, (24 + random.randint(-10, 10), 93 + random.randint(-10, 10)))
  return im


plugin_dir = os.path.dirname(os.path.abspath(__file__))

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
  command.CommandBuilder("petpet_v2.indihome", "indihome", "印尼宽带", "印尼", "宽带")
  .category("petpet_v2")
  .brief("叮~")
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
  avatar = avatar.resize((360, 360), Image.ANTIALIAS)
  circle(avatar)
  frames: list[Image.Image] = []
  durations: list[int] = []
  for i in range(SLIDE_FRAMES):
    im = Image.new("RGB", (360, 360), (255, 255, 255))
    im.paste(avatar, lerp((360, 0), (0, 0), i / SLIDE_FRAMES), avatar)
    frames.append(im)
    durations.append(SLIDE_DURATION // SLIDE_FRAMES)
  avatar_im = Image.new("RGBA", (360, 360), (255, 255, 255, 255))
  avatar_im.paste(avatar, AVATAR_BOX, avatar)
  frames.append(avatar_im)
  durations.append(AVATAR_DURATION)
  white = Image.new("RGB", (360, 360), (255, 255, 255))
  price_bg_im = Image.open(os.path.join(plugin_dir, "template.png"))
  price_fg_im = Image.open(os.path.join(plugin_dir, "text.png"))
  for i in range(SCALE_FRAMES):
    ratio = (i + 1) / (SCALE_FRAMES + 1)
    price_im = make_price_im(price_bg_im, price_fg_im)
    im = Image.blend(white, price_im, ratio)
    paste(im, avatar, lerp(AVATAR_BOX, PRICE_BOX, ratio))
    frames.append(im)
    durations.append(SCALE_DURATION // SCALE_FRAMES)
  for i in range(PRICE_FRAMES):
    price_im = make_price_im(price_bg_im, price_fg_im)
    paste(price_im, avatar, PRICE_BOX)
    frames.append(price_im)
    durations.append(PRICE_DURATION // PRICE_FRAMES)
  await matcher.finish(segment_animated_image(args.format, frames, durations))
