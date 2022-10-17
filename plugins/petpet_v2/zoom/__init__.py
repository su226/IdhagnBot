from argparse import Namespace
from pathlib import Path
import asyncio

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, util

from ..util import get_image_and_user

DIR = Path(__file__).resolve().parent
BOXES = [
  (-222, 30, 695, 430), (-212, 30, 695, 430), (0, 30, 695, 430), (41, 26, 695, 430),
  (-100, -67, 922, 570), (-172, -113, 1059, 655), (-273, -192, 1217, 753)
]
BOX_IDS = [0, 0, 0, 1, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 5, 6, 6, 6, 6]
FRAMETIME = 200

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

matcher = command.CommandBuilder("petpet_v2.zoom", "放大") \
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
    frames: list[Image.Image] = []
    for i, raw in zip(range(24), util.sample_frames(target, FRAMETIME)):
      x, y, w, h = BOXES[BOX_IDS[i]]
      fg = ImageOps.pad(raw.convert("RGBA"), (w, h), util.scale_resample)
      fg = fg.rotate(4.2, util.resample, True)
      template = Image.open(DIR / f"{i}.png").convert("RGBA")
      im = Image.new("RGB", template.size)
      im.paste(fg, (x, y), fg)
      im.paste(template, mask=template)
      frames.append(im)
    return util.pil_image(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
