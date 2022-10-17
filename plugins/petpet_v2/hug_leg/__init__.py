import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, util

from ..util import get_image_and_user

DIR = Path(__file__).resolve().parent
FRAMETIME = 60
BOXES = [
  (50, 73, 68, 92), (58, 60, 62, 95), (65, 10, 67, 118), (61, 20, 77, 97), (55, 44, 65, 106),
  (66, 85, 60, 98)
]

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接"
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

matcher = command.CommandBuilder("petpet_v2.hug_leg", "抱大腿") \
  .category("petpet_v2") \
  .shell(parser) \
  .auto_reject() \
  .build()
@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  try:
    target, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  def make() -> MessageSegment:
    frames: list[Image.Image] = []
    for i, box in enumerate(BOXES):
      template = Image.open(DIR / f"{i}.png")
      im = Image.new("RGB", template.size, (255, 255, 255))
      x, y, w, h = box
      resized = target.resize((w, h), util.scale_resample)
      im.paste(resized, (x, y), resized)
      im.paste(template, mask=template)
      frames.append(im)
    return util.pil_image(frames, FRAMETIME, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
