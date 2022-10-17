import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, util

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

matcher = command.CommandBuilder("petpet_v2.blood_pressure", "血压") \
  .brief("[动]") \
  .category("petpet_v2") \
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
    template = Image.open(DIR / "template.png")
    frames: list[Image.Image] = []
    for raw in util.frames(target):
      fg = ImageOps.fit(raw.convert("RGBA"), (414, 450), util.scale_resample)
      im = Image.new("RGB", template.size, (255, 255, 255))
      im.paste(fg, (16, 17), fg)
      im.paste(template, mask=template)
      frames.append(im)
    return util.pil_image(frames, target, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
