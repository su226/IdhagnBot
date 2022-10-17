import asyncio
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, text, util

from ..util import get_image_and_user

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

matcher = command.CommandBuilder("petpet_v2.keep", "一直") \
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
    text1 = text.render("要我一直", "sans", 60)
    text2 = text.render("吗", "sans", 60)

    frames: list[Image.Image] = []
    for raw in util.frames(target):
      raw = raw.convert("RGBA")
      big = util.resize_width(raw, 500)
      small = util.resize_width(raw, 100)
      text_h = max(small.height, text1.height, text2.height)
      im = Image.new("RGB", (big.width, big.height + text_h), (255, 255, 255))
      im.paste(big, mask=big)
      x = (im.width - small.width - text1.width - text2.width) // 2
      y = big.height + text_h // 2
      im.paste(text1, (x, y - text1.height // 2), text1)
      x += text1.width
      im.paste(small, (x, y - small.height // 2), small)
      x += small.width
      im.paste(text2, (x, y - text2.height // 2), text2)
      frames.append(im)

    return util.pil_image(frames, target, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
