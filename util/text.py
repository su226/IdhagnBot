from typing import Literal, cast, overload
from PIL import Image
import cairo
import gi
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo

WRAP_WORD = 0
WRAP_CHAR = 1
WRAP_WORD_CHAR = 2
ELLIPSIZE_START = 3
ELLIPSIZE_MIDDLE = 4
ELLIPSIZE_END = 5
Mode = Literal[0, 1, 2, 3, 4, 5]

def layout(content: str, font: str, size: float, *, box: tuple[int, int] | int | None = None, mode: Mode = 0, markup: bool = False) -> Pango.Layout:
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
  if markup:
    layout.set_markup(content, -1)
  else:
    layout.set_text(content, -1)
  return layout

@overload
def render(content: Pango.Layout, *, color: tuple[int, int, int] = (0, 0, 0)) -> Image.Image: ...
@overload
def render(content: str, font: str, size: float, *, color: tuple[int, int, int] = (0, 0, 0), box: tuple[int, int] | int | None = None, mode: Mode = 0, markup: bool = False) -> Image.Image: ...
def render(content: str | Pango.Layout, *args, color: tuple[int, int, int] = (0, 0, 0), **kw) -> Image.Image:
  if isinstance(content, Pango.Layout):
    l = content
  else:
    l = layout(content, *args, **kw)
  w, h = l.get_pixel_size()
  with cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h) as surface:
    cr = cairo.Context(surface)
    cr.set_source_rgb(color[0] / 255, color[1] / 255, color[2] / 255)
    PangoCairo.show_layout(cr, l)
    im = Image.frombytes("RGBA", (w, h), bytes(surface.get_data()))
  b, g, r, a = im.split() # 交换红蓝通道，因为PIL不支持Cairo用的BGRa
  return Image.merge("RGBa", (r, g, b, a))
