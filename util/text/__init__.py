import math
from typing import Literal, overload

import cairo
import gi
from PIL import Image

from util.color import RGB, split_rgb

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # type: ignore

WRAP_WORD = 0
WRAP_CHAR = 1
WRAP_WORD_CHAR = 2
ELLIPSIZE_START = 3
ELLIPSIZE_MIDDLE = 4
ELLIPSIZE_END = 5
Mode = Literal[0, 1, 2, 3, 4, 5]
Anchor = Literal["lt", "lm", "lb", "mt", "mm", "mb", "rt", "rm", "rb"]
Align = Literal["l", "m", "r"]


def layout(
  content: str, font: str, size: float, *, box: tuple[int, int] | int | None = None, mode: Mode = 0,
  markup: bool = False, align: Align = "l", spacing: int = 0
) -> Pango.Layout:
  context = Pango.Context()
  context.set_font_map(PangoCairo.FontMap.get_default())
  layout = Pango.Layout(context)
  desc = Pango.FontDescription.from_string(font)
  desc.set_absolute_size(Pango.SCALE * size)
  layout.set_font_description(desc)
  if box is not None:
    if isinstance(box, tuple):
      layout.set_width(box[0] * Pango.SCALE)
      layout.set_height(box[1] * Pango.SCALE)
    else:
      layout.set_width(box * Pango.SCALE)
    if mode > 2:
      layout.set_ellipsize(mode - 2)
    else:
      layout.set_wrap(mode)
  layout.set_spacing(spacing)
  if align == "m":
    layout.set_alignment(Pango.Alignment.CENTER)
  if align == "r":
    layout.set_alignment(Pango.Alignment.RIGHT)
  if markup:
    layout.set_markup(content, -1)
  else:
    layout.set_text(content, -1)
  return layout


@overload
def render(
  content: Pango.Layout, *, color: RGB | int = ..., stroke: float = ...,
  stroke_color: RGB | int = ...
) -> Image.Image: ...


@overload
def render(
  content: str, font: str, size: float, *, color: RGB | int = ..., stroke: float = ...,
  stroke_color: RGB | int = ..., box: tuple[int, int] | int | None = ..., mode: Mode = ...,
  markup: bool = ..., align: Align = ..., spacing: int = ...
) -> Image.Image: ...


def render(
  content: str | Pango.Layout, *args, color: RGB | int = (0, 0, 0), stroke: float = 0,
  stroke_color: RGB | int = (255, 255, 255), **kw
) -> Image.Image:
  if isinstance(content, Pango.Layout):
    l = content
  else:
    l = layout(content, *args, **kw)
  w, h = l.get_pixel_size()  # type: ignore
  margin = math.ceil(stroke)
  w += margin * 2
  h += margin * 2
  with cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h) as surface:
    cr = cairo.Context(surface)
    if stroke:
      if isinstance(stroke_color, int):
        stroke_color = split_rgb(stroke_color)
      cr.move_to(margin, margin)
      PangoCairo.layout_path(cr, l)
      cr.set_line_width(stroke * 2)
      cr.set_source_rgb(stroke_color[0] / 255, stroke_color[1] / 255, stroke_color[2] / 255)
      cr.stroke()
    if isinstance(color, int):
      color = split_rgb(color)
    cr.move_to(margin, margin)
    cr.set_source_rgb(color[0] / 255, color[1] / 255, color[2] / 255)
    PangoCairo.show_layout(cr, l)
    data = surface.get_data()
    if data:  # 如果文字为空，图片大小是0x0，data为None
      im = Image.frombytes("RGBA", (w, h), bytes(data))
    else:
      return Image.new("RGBA", (w, h))
  b, g, r, a = im.split()  # 交换红蓝通道，因为PIL不支持Cairo用的BGRa
  return Image.merge("RGBa", (r, g, b, a)).convert("RGBA")  # type: ignore


@overload
def paste(
  im: Image.Image, xy: tuple[int, int], content: Pango.Layout, *, anchor: Anchor = ...,
  color: RGB | int = ..., stroke: float = ..., stroke_color: RGB | int = ...
) -> Image.Image: ...


@overload
def paste(
  im: Image.Image, xy: tuple[int, int], content: str, font: str, size: float, *,
  anchor: Anchor = ..., color: RGB | int = ..., stroke: float = ..., stroke_color: RGB | int = ...,
  box: tuple[int, int] | int | None = ..., mode: Mode = ..., markup: bool = ..., align: Align = ...,
  spacing: int = ...
) -> Image.Image: ...


def paste(im: Image.Image, xy: tuple[int, int], *args, anchor: Anchor = "lt", **kw) -> Image.Image:
  text = render(*args, **kw)
  x, y = xy
  xa, ya = anchor
  if xa == "m":
    x -= text.width // 2
  elif xa == "r":
    x -= text.width
  if ya == "m":
    y -= text.height // 2
  elif ya == "b":
    y -= text.height
  im.paste(text, (x, y), text)
  return text
