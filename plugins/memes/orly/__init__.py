import random
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import colorutil, command, context, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent
COLORS = [
  (97, 0, 94), (112, 112, 109), (137, 0, 41), (196, 0, 14), (109, 0, 29), (106, 0, 189),
  (241, 0, 0), (0, 113, 177), (249, 188, 0), (44, 0, 119), (186, 0, 154), (0, 144, 71),
  (0, 157, 158), (34, 46, 133), (189, 0, 46), (0, 157, 26), (117, 165, 0),
]
IMAGES = [
  "44412_rabbits.png", "44451_dog.png", "48582_common_frog.png", "51617_caribou.png",
  "53217_agaric_cep.png", "56818_field-mouse.png", "61091_stink_bug.png", "62311_tachina_fly.png",
  "64791_crst_pelican.png", "65125_lb_cockatoo.png", "65378_sp_sunbird.png",
  "72929_pugnose_bat.png", "72978_giraffeleaf.png", "80808_holsteincow.png", "87344_peacock.png",
  "87856_dalmatian.png", "87951_plant-bug.png", "baboon_2.png", "beefcow_12092.png",
  "bighorngt_15210.png", "butterfly_2.png", "cat_1.png", "cat_3.png", "cat_16997.png",
  "coyote_21233.png", "crab_8248.png", "crossspider_22983.png", "deer_1.png", "domestic_12615.png",
  "dragonfly_1.png", "duckbill_7049.png", "electricray_13697.png", "gorilla_11100.png",
  "grizzly-bear_1.png", "horse_2.png", "oar-fish_27235.png", "ostrich_21849.png",
  "potato_21766.png", "rabbit4_21005.png", "sheepshead_11384.png", "shrimp_14982.png",
  "speedhorse_12088.png",
]

parser = ArgumentParser(add_help=False)
parser.add_argument("title1", help="标题第一行")
parser.add_argument("title2", nargs="?", default="", help="标题第二行")
parser.add_argument("--header", "-h", default="", help="页眉")
parser.add_argument("--subtitle", "-s", default="", help="副标题")
parser.add_argument("--position", "-p",
  choices=["左上", "左下", "右上", "右下", "lt", "lb", "rt", "rb"], default="rb",
  help="副标题方位",
)
parser.add_argument("--author", "-a", default="", help="作者（默认为昵称）")
parser.add_argument("--color", "-c", help=(
  "颜色，0-16为内置颜色，也可是颜色代码，默认为内置颜色中随机"
))
parser.add_argument("--image", "-i", help=(
  "图片，0-41为内置图片，也可是@、QQ号、昵称、群名片或图片链接，默认为内置图片中随机"
))
parser.add_argument("--no-grayscale", "-G", action="store_true", help="不对下载的图片去色")
orly = (
  command.CommandBuilder("memes.orly", "orly", "动物书")
  .category("memes")
  .brief("学计算机的应该不陌生")
  .shell(parser)
  .build()
)
@orly.handle()
async def handle_orly(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  if "\n" in args.title1 or "\n" in args.title2 or "\n" in args.subtitle or "\n" in args.author:
    await orly.finish("内容不能有换行")
  if args.color is None:
    c = random.choice(COLORS)
  else:
    try:
      c = COLORS[int(args.color)]
    except (ValueError, KeyError):
      c = colorutil.parse(args.color)
      if c is None:
        await orly.finish(f"无效颜色：{args.color}")
  if not args.author:
    author = await context.get_card_or_name(bot, event, event.user_id)
  else:
    author = args.author
  if args.image is None:
    cover_task = random.choice(IMAGES)
  else:
    try:
      cover_task = IMAGES[int(args.image)]
    except (ValueError, KeyError):
      async with AvatarGetter(bot, event) as g:
        cover_task = g(args.image, DefaultType.TARGET)

  def make() -> MessageSegment:
    if isinstance(cover_task, str):
      cover = Image.open(DIR / cover_task)
    else:
      cover, _ = cover_task.result()
    cover = ImageOps.contain(cover, (920, 707), imutil.scale_resample())
    if not args.no_grayscale:
      cover = cover.convert("L")
    im = Image.new("RGB", (1000, 1400), (255, 255, 255))
    im.paste(cover, (960 - cover.width, 802 - cover.height))
    rect_y = 802
    if args.position in ("左上", "lt"):
      text_im = textutil.paste(im, (40, 801), args.subtitle, "sans medium", 39, anchor="lb")
      rect_y += text_im.height
    elif args.position in ("左下", "lb"):
      textutil.paste(im, (40, 1072), args.subtitle, "sans medium", 39, anchor="lt")
    elif args.position in ("右上", "rt"):
      text_im = textutil.paste(im, (959, 801), args.subtitle, "sans medium", 39, anchor="rb")
      rect_y += text_im.height
    else:
      textutil.paste(im, (959, 1072), args.subtitle, "sans medium", 39, anchor="rt")
    im.paste(c, (40, 0, 960, 19))
    im.paste(c, (40, rect_y, 960, rect_y + 270))
    textutil.paste(im, (500, 19), args.header, "sans medium", 28, anchor="mt")
    if args.title2:
      textutil.paste(
        im, (68, rect_y + 144), args.title1, "serif bold", 77, anchor="lb", color=(255, 255, 255))
      textutil.paste(
        im, (68, rect_y + 236), args.title2, "serif bold", 77, anchor="lb", color=(255, 255, 255))
    else:
      textutil.paste(
        im, (68, rect_y + 247), args.title1, "serif bold", 118, anchor="lb", color=(255, 255, 255))
    textutil.paste(im, (944, 1353), author, "sans medium", 33, anchor="rb")
    textutil.paste(im, (56, 1356), "O'RLY?", "sans heavy", 44, anchor="lb")
    return imutil.to_segment(im)

  await orly.finish(await misc.to_thread(make))
