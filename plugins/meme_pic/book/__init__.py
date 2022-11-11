import asyncio
import re
from argparse import Namespace
from pathlib import Path

import gi
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

gi.require_version("Pango", "1.0")
from gi.repository import Pango  # type: ignore

from util import command, imutil, textutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
CHINESE_RE = re.compile(r"[\u4e00-\u9fa5]+")
# RemapTransform((1000, 1100), ((0, 108), (1092, 0), (1023, 1134), (29, 1134)))  # noqa
OLD_SIZE = (1000, 1100)
NEW_SIZE = (1092, 1134)
TRANSFORM = (
  1.000187203406968, -0.028270398536847364, 3.0532030419797866, 0.09595548725148711,
  0.9702165933205678, -104.78339207862291, 8.723226113771426e-05, -8.382056698179919e-05
)


def render_vertical_text(content: str, font: str, size: int, **kw) -> Image.Image:
  lines: list[tuple[int, list[Image.Image]]] = []
  total_width = 0
  total_height = 0
  for line in content.splitlines():
    parts: list[Image.Image] = []
    width = 0
    height = 0

    pos = 0
    while match := CHINESE_RE.search(line, pos):
      im = textutil.render(line[pos:match.start()], font, size, **kw)
      parts.append(im)
      width += im.width
      height = max(height, im.height)

      layout = textutil.layout(match[0], font, size)
      desc = layout.get_font_description()
      desc.set_gravity(Pango.Gravity.EAST)
      layout.set_font_description(desc)
      im = textutil.render(layout, **kw)
      parts.append(im)
      width += im.width
      height = max(height, im.height)

      pos = match.end()

    im = textutil.render(line[pos:], font, size, **kw)
    parts.append(im)
    width += im.width
    height = max(height, im.height)

    lines.append((height, parts))
    total_width = max(total_width, width)
    total_height += height

  im = Image.new("RGBA", (total_width, total_height))
  y = 0
  for height, parts in lines:
    x = 0
    for part in parts:
      im.paste(part, (x, y + (height - part.height) // 2))
      x += part.width
    y += height
  return im.transpose(Image.Transpose.ROTATE_270)


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--text", "-t", default="", metavar="文本", help=(
  "书脊上的书名，中文竖排"
))
matcher = (
  command.CommandBuilder("meme_pic.book", "看书")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    template = Image.open(DIR / "template.png")
    target = ImageOps.fit(target, OLD_SIZE, imutil.scale_resample())
    target = target.transform(NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, imutil.resample())
    im = Image.new("RGB", template.size, (255, 255, 255))
    im.paste(target, (1138, 1172), target)
    im.paste(template, mask=template)

    if args.text:
      text_im = render_vertical_text(args.text, "sans bold", 200, color=(255, 255, 255))
      text_im = imutil.contain_down(text_im, 240, 780)
      text_im = text_im.rotate(3, imutil.resample(), True)
      imutil.paste(im, text_im, (990, 1890), anchor="mm")

    return imutil.to_segment(im)

  await matcher.finish(await asyncio.to_thread(make))
