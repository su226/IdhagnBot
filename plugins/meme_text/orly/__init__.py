import asyncio
import os
import random
import re
from argparse import Namespace
from io import BytesIO

import aiohttp
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment, unescape
from nonebot.exception import ActionFailed, ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw, ImageOps

from util import color, command, context, text, util

plugin_dir = os.path.dirname(os.path.abspath(__file__))
COLORS = [
  (97, 0, 94), (112, 112, 109), (137, 0, 41), (196, 0, 14), (109, 0, 29), (106, 0, 189),
  (241, 0, 0), (0, 113, 177), (249, 188, 0), (44, 0, 119), (186, 0, 154), (0, 144, 71),
  (0, 157, 158), (34, 46, 133), (189, 0, 46), (0, 157, 26), (117, 165, 0)]
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
  "speedhorse_12088.png"]
IMAGE_RE = re.compile(r"^\[CQ:image[^\]]+\]$")


async def download_image(url: str, no_grayscale: bool) -> Image.Image:
  async with aiohttp.ClientSession() as http:
    async with http.get(url) as response:
      im = Image.open(BytesIO(await response.read())).convert("RGBA")
  im2 = Image.new("RGB", im.size, (255, 255, 255))
  im2.paste(im, mask=im)
  if not no_grayscale:
    return im2.convert("L")
  return im2


parser = ArgumentParser(add_help=False)
parser.add_argument("title1", help="标题第一行")
parser.add_argument("title2", nargs="?", default="", help="标题第二行")
parser.add_argument("-header", default="", help="页眉")
parser.add_argument("-subtitle", default="", help="副标题")
parser.add_argument(
  "-position", choices=["左上", "左下", "右上", "右下", "lt", "lb", "rt", "rb"], default="rb",
  help="副标题方位")
parser.add_argument("-author", help="作者（默认为昵称）")
parser.add_argument("-color", help="颜色，0-16为内置颜色，也可是颜色代码，默认为内置颜色中随机")
parser.add_argument("-image", help="图片，0-41为内置图片，也可是链接，默认为内置图片中随机")
parser.add_argument("-no-grayscale", action="store_true", help="不对下载的图片去色")
orly = (
  command.CommandBuilder("meme_text.orly", "orly", "动物书")
  .brief("学计算机的应该不陌生")
  .shell(parser)
  .build())


@orly.handle()
async def handle_orly(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await orly.finish(args.message)
  if args.author is None:
    try:
      info = await bot.get_group_member_info(
        group_id=context.get_event_context(event), user_id=event.user_id)
      author = info["card"] or info["nickname"]
    except ActionFailed:
      author = (await bot.get_stranger_info(user_id=event.user_id))["nickname"]
  else:
    author = args.author
  if "\n" in args.title1 or "\n" in args.title2 or "\n" in args.subtitle or "\n" in author:
    await orly.finish("内容不能有换行")
  if args.color is None:
    c = random.choice(COLORS)
  else:
    try:
      c = COLORS[int(args.color)]
    except (ValueError, KeyError):
      c = color.parse(args.color)
      if c is None:
        await orly.finish(f"无效颜色：{args.color}")
  if args.image is None:
    cover = Image.open(os.path.join(plugin_dir, random.choice(IMAGES)))
  else:
    if args.image == "-":
      await orly.send("请发送一张图片")
      url = await util.prompt(event)
      try:
        url = url["image", 0].data["url"]
      except IndexError:
        url = url.extract_plain_text()
    else:
      url = unescape(args.image)
    try:
      cover = Image.open(os.path.join(plugin_dir, IMAGES[int(url)]))
    except (ValueError, KeyError):
      try:
        cover = await asyncio.wait_for(download_image(url, args.no_grayscale), 10)
      except asyncio.TimeoutError:
        await orly.finish(f"下载超时：{url}")
      except aiohttp.ClientError:
        await orly.finish(f"下载失败：{url}")
      except Exception:
        await orly.finish(f"无效图片：{url}")
  cover = ImageOps.contain(cover, (920, 707), util.scale_resample)
  im = Image.new("RGB", (1000, 1400), (255, 255, 255))
  im.paste(cover, (960 - cover.width, 802 - cover.height))
  rect_y = 802
  if args.position in ("左上", "lt"):
    text_im = text.paste(im, (40, 801), args.subtitle, "sans medium", 39, anchor="lb")
    rect_y += text_im.height
  elif args.position in ("左下", "lb"):
    text.paste(im, (40, 1072), args.subtitle, "sans medium", 39, anchor="lt")
  elif args.position in ("右上", "rt"):
    text_im = text.paste(im, (959, 801), args.subtitle, "sans medium", 39, anchor="rb")
    rect_y += text_im.height
  else:
    text.paste(im, (959, 1072), args.subtitle, "sans medium", 39, anchor="rt")
  draw = ImageDraw.Draw(im)
  draw.rectangle((40, 0, 959, 18), c)
  draw.rectangle((40, rect_y, 959, rect_y + 269), c)
  text.paste(im, (500, 19), args.header, "sans medium", 28, anchor="mt")
  if args.title2:
    text.paste(
      im, (68, rect_y + 144), args.title1, "serif bold", 77, anchor="lb", color=(255, 255, 255))
    text.paste(
      im, (68, rect_y + 236), args.title2, "serif bold", 77, anchor="lb", color=(255, 255, 255))
  else:
    text.paste(
      im, (68, rect_y + 247), args.title1, "serif bold", 118, anchor="lb", color=(255, 255, 255))
  text.paste(im, (944, 1353), author, "sans medium", 33, anchor="rb")
  text.paste(im, (56, 1356), "O'RLY?", "sans heavy", 44, anchor="lb")
  f = BytesIO()
  im.save(f, "png")
  await orly.finish(MessageSegment.image(f))
