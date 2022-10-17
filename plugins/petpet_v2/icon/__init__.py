import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, text, util

from ..util import get_image_and_user

DIR = Path(__file__).resolve().parent
TEXT_WIDTH = 1170
TEXT_HEIGHT = 210

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接"
)
parser.add_argument(
  "--text", "-t", default="朋友\n先看看这个图标再说话", metavar="文本",
  help="默认为“朋友 先看看这个图标再说话”"
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

matcher = command.CommandBuilder("petpet_v2.icon", "看图标") \
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
    text_im = text.render(args.text, "sans", 100, align="m")
    text_im = util.contain_down(text_im, TEXT_WIDTH, TEXT_HEIGHT)
    util.paste(template, text_im, (585, 1038), anchor="mm")
    frames: list[Image.Image] = []
    for raw in util.frames(target):
      fg = ImageOps.fit(raw.convert("RGBA"), (515, 515), util.scale_resample)
      im = Image.new("RGB", template.size, (255, 255, 255))
      im.paste(fg, (599, 403), fg)
      im.paste(template, mask=template)
      frames.append(im)
    return util.pil_image(frames, target, afmt=args.format)

  await matcher.finish(await asyncio.to_thread(make))
