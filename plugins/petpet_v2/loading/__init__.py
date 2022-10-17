from argparse import Namespace
from pathlib import Path
import asyncio

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageEnhance, ImageFilter

from util import command, text, util

from ..util import get_image_and_user

DIR = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接（可传入动图）"
)
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式（如果传入动图）"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式（如果传入动图）"
)

matcher = command.CommandBuilder("petpet_v2.loading", "加载中") \
  .category("petpet_v2") \
  .brief("[动]") \
  .shell(parser) \
  .auto_reject() \
  .build()
@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  try:
    target, _ = await get_image_and_user(bot, event, args.target, event.self_id, raw=True)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  def make() -> MessageSegment:
    big = util.resize_width(target.convert("RGBA"), 500)
    mask = Image.new("RGB", big.size, (255, 255, 255))
    mask.paste(big, mask=big)
    mask = ImageEnhance.Brightness(mask).enhance(0.5)
    mask = mask.filter(ImageFilter.GaussianBlur(3))
    icon = Image.open(DIR / "icon.png")
    util.paste(mask, icon, (big.width // 2, big.height // 2), anchor="mm")
    text1 = text.render("不出来", "sans", 60)

    frames: list[Image.Image] = []
    for raw in util.frames(target):
      small = util.resize_width(raw.convert("RGBA"), 100)
      text_h = max(small.height, text1.height)
      im = Image.new("RGB", (big.width, big.height + text_h), (255, 255, 255))
      im.paste(mask)
      x = (im.width - small.width - text1.width) // 2
      y = big.height + text_h // 2
      im.paste(small, (x, y - small.height // 2), small)
      x += small.width
      im.paste(text1, (x, y - text1.height // 2), text1)
      frames.append(im)

    return util.pil_image(frames, target, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
