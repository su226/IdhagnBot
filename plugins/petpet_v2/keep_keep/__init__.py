import asyncio
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, text, util

from ..util import get_image_and_user

FRAMETIME = 100

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接（可传入动图）"
)
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式"
)

matcher = command.CommandBuilder("petpet_v2.keep_keep", "一直一直") \
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
    small_h = target.height * 125 // target.width
    text_h = max(small_h, text1.height, text2.height)

    base_scale = 5 ** (1 / 20)

    frames: list[Image.Image] = []
    for i, raw in zip(range(20), util.sample_frames(target, FRAMETIME)):
      raw = raw.convert("RGBA")
      big = util.resize_width(raw, 500)
      im_one = Image.new("RGB", (500, big.height + text_h), "white")
      x = (im_one.width - 100 - text1.width - text2.width) // 2
      y = big.height + text_h // 2
      im_one.paste(text1, (x, y - text1.height // 2), text1)
      x += text1.width + 100
      im_one.paste(text2, (x, y - text2.height // 2), text2)
      im_one.paste(big, mask=big)
      im = Image.new("RGB", im_one.size, (255, 255, 255))
      scale = base_scale ** i
      for _ in range(4):
        x = int(358 * (1 - scale))
        y = int(im.height * (1 - scale))
        w = int(500 * scale)
        h = int(im.height * scale)
        im.paste(im_one.resize((w, h)), (x, y))
        scale /= 5
      frames.append(im)

    return util.pil_image(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
