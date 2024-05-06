import math
import random
from typing import List

import cairo
import gi
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageChops

from util import command, imutil, misc, textutil

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # noqa: E402  # type: ignore

FONT_SIZE = 64
SHEAR = FONT_SIZE * -0.32
BG = (28, 11, 27)
FG1 = (0, 242, 234)
FG2 = (255, 255, 255)
FG3 = (255, 0, 79)
PADDING = 32
DISPERSION = 3
FRAMES = 10
SHIFT = 5


def render_sheared(layout: Pango.Layout) -> Image.Image:
  _, rect = layout.get_pixel_extents()
  x = -rect.x
  width = rect.width + math.ceil(abs(SHEAR))
  with cairo.ImageSurface(cairo.FORMAT_ARGB32, width, rect.height) as surface:
    cr = cairo.Context(surface)
    y = -rect.y
    for line in layout.get_lines_readonly():
      _, rect = line.get_pixel_extents()
      k = SHEAR / rect.height
      b = -k * y
      if SHEAR < 0:
        b -= SHEAR
      cr.set_matrix(cairo.Matrix(1, 0, k, 1, b, 0))
      cr.move_to(x, y - rect.y)
      cr.set_source_rgb(1, 1, 1)
      PangoCairo.show_layout_line(cr, line)
      y += rect.height
    return imutil.from_cairo(surface)


tiktok = (
  command.CommandBuilder("meme_word.tiktok", "抖音", "tiktok")
  .category("meme_word")
  .brief("记录每种生物")
  .usage("/抖音 <文本>")
  .build()
)
@tiktok.handle()
async def handle_tiktok(args: Message = CommandArg()):
  def make() -> MessageSegment:
    text = args.extract_plain_text().rstrip() or tiktok.__doc__ or ""
    center = render_sheared(textutil.layout(text, "sans bold", FONT_SIZE))
    w, h = center.size
    topleft = Image.new("L", (w, h))
    topleft.paste(center, mask=center)
    shifted = Image.new("L", (w, h))
    shifted.paste(topleft, (-DISPERSION, -DISPERSION))
    bottomright = ImageChops.subtract(topleft, shifted)
    text_im = Image.new("RGB", (w + DISPERSION, h + DISPERSION), BG)
    text_im.paste(FG1, (0, 0), topleft)
    text_im.paste(FG2, (DISPERSION, DISPERSION), center)
    text_im.paste(FG3, (DISPERSION, DISPERSION), bottomright)

    segments = max(int(6 * text_im.height / 90), 2)
    size = (text_im.width + PADDING * 2, text_im.height + PADDING * 2)
    frames: List[Image.Image] = []
    for _ in range(FRAMES):
      im = Image.new("RGB", size, BG)
      heights = random.sample(range(1, text_im.height), segments - 1)
      heights.sort()
      last_y = 0
      for y in heights:
        shift = random.randint(-SHIFT, SHIFT)
        im.paste(
          text_im.crop((0, last_y, text_im.width, y)),
          (PADDING + shift, PADDING + last_y)
        )
        last_y = y
      shift = random.randint(-SHIFT, SHIFT)
      im.paste(
        text_im.crop((0, last_y, text_im.width, text_im.height)),
        (PADDING + shift, PADDING + last_y)
      )
      frames.append(im)

    return imutil.to_segment(frames, 200)
  await tiktok.finish(await misc.to_thread(make))
