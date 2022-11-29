import math
from typing import Dict, Literal, Tuple, Union, overload

import cairo
import gi
from PIL import Image

from util import imutil, misc
from util.colorutil import RGB, split_rgb

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import GLib, Pango, PangoCairo  # type: ignore

Wrap = Literal["word", "char", "word_char"]
Ellipsize = Literal[None, "start", "middle", "end"]
Align = Literal["l", "m", "r"]
WRAPS: Dict[Wrap, Pango.WrapMode] = {
  "word": Pango.WrapMode.WORD,
  "char": Pango.WrapMode.CHAR,
  "word_char": Pango.WrapMode.WORD_CHAR,
}
ELLIPSIZES: Dict[Ellipsize, Pango.EllipsizeMode] = {
  None: Pango.EllipsizeMode.NONE,
  "start": Pango.EllipsizeMode.START,
  "middle": Pango.EllipsizeMode.MIDDLE,
  "end": Pango.EllipsizeMode.END,
}
ANTIALIASES: Dict[misc.CairoAntialias, cairo.Antialias] = {
  "default": cairo.Antialias.DEFAULT,
  "none": cairo.Antialias.NONE,
  "fast": cairo.Antialias.FAST,
  "good": cairo.Antialias.GOOD,
  "best": cairo.Antialias.BEST,
  "gray": cairo.Antialias.GRAY,
  "subpixel": cairo.Antialias.SUBPIXEL,
}
SUBPIXEL_ORDERS: Dict[misc.CairoSubpixel, cairo.SubpixelOrder] = {
  "default": cairo.SubpixelOrder.DEFAULT,
  "rgb": cairo.SubpixelOrder.RGB,
  "bgr": cairo.SubpixelOrder.BGR,
  "vrgb": cairo.SubpixelOrder.VRGB,
  "vbgr": cairo.SubpixelOrder.VBGR,
}
HINT_METRICS: Dict[misc.CairoHintMetrics, cairo.HintMetrics] = {
  "default": cairo.HintMetrics.DEFAULT,
  False: cairo.HintMetrics.OFF,
  True: cairo.HintMetrics.ON,
}
HINT_STYLES: Dict[misc.CairoHintStyle, cairo.HintStyle] = {
  "default": cairo.HintStyle.DEFAULT,
  "none": cairo.HintStyle.NONE,
  "slight": cairo.HintStyle.SLIGHT,
  "medium": cairo.HintStyle.MEDIUM,
  "full": cairo.HintStyle.FULL,
}


def special_font(name: str, fallback: str) -> str:
  if value := misc.CONFIG().special_font.get(name, None):
    return value
  return fallback


def font_options(context: Union[None, Pango.Context, cairo.Context] = None) -> cairo.FontOptions:
  config = misc.CONFIG()
  options = cairo.FontOptions()
  options.set_antialias(ANTIALIASES[config.text_antialias])
  options.set_subpixel_order(SUBPIXEL_ORDERS[config.text_subpixel])
  options.set_hint_metrics(HINT_METRICS[config.text_hint_metrics])
  options.set_hint_style(HINT_STYLES[config.text_hint_style])
  if isinstance(context, Pango.Context):
    PangoCairo.context_set_font_options(context, options)
  elif isinstance(context, cairo.Context):
    context.set_font_options(options)
  return options


def layout(
  content: str, font: str, size: float, *, box: Union[Tuple[int, int], int, None] = None,
  wrap: Wrap = "word", ellipsize: Ellipsize = None, markup: bool = False, align: Align = "l",
  spacing: int = 0, lines: int = 0
) -> Pango.Layout:
  context = Pango.Context()  # Pango.Context 线程不安全，复用会有奇怪的问题
  font_options(context)
  context.set_font_map(PangoCairo.FontMap.get_default())
  layout = Pango.Layout(context)
  if value := misc.CONFIG().font_substitute.get(font, None):
    font = value
  desc = Pango.FontDescription.from_string(font)
  desc.set_absolute_size(Pango.SCALE * size)
  layout.set_font_description(desc)
  if box is not None:
    if isinstance(box, tuple):
      layout.set_width(box[0] * Pango.SCALE)
      layout.set_height(box[1] * Pango.SCALE)
    else:
      layout.set_width(box * Pango.SCALE)
  layout.set_ellipsize(ELLIPSIZES[ellipsize])
  layout.set_wrap(WRAPS[wrap])
  spacing *= Pango.SCALE
  layout.set_spacing(spacing)
  if lines:
    # 使用Pango.FontMetrics.get_height获取到的行高可能差一像素
    # 直接获取空Layout的高度即为一倍行高
    line_height = layout.get_size().height
    layout.set_height(line_height * lines + spacing * (lines - 1))
  if align == "m":
    layout.set_alignment(Pango.Alignment.CENTER)
  if align == "r":
    layout.set_alignment(Pango.Alignment.RIGHT)
  if markup:
    try:
      Pango.parse_markup(content, -1, "\0")
    except GLib.Error as e:
      layout.set_text(f"解析失败: {e.message}", -1)
    else:
      layout.set_markup(content, -1)
  else:
    layout.set_text(content, -1)
  return layout


@overload
def render(
  content: Pango.Layout, *, color: Union[RGB, int] = ..., stroke: float = ...,
  stroke_color: Union[RGB, int] = ...
) -> Image.Image: ...
@overload
def render(
  content: str, font: str, size: float, *, color: Union[RGB, int] = ..., stroke: float = ...,
  stroke_color: Union[RGB, int] = ..., box: Union[Tuple[int, int], int, None] = ...,
  wrap: Wrap = ..., ellipsize: Ellipsize = ..., markup: bool = ..., align: Align = ...,
  spacing: int = ..., lines: int = ...
) -> Image.Image: ...
def render(
  content: Union[str, Pango.Layout], *args, color: Union[RGB, int] = (0, 0, 0), stroke: float = 0,
  stroke_color: Union[RGB, int] = (255, 255, 255), **kw
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
    return imutil.from_cairo(surface)


@overload
def paste(
  im: Image.Image, xy: Tuple[int, int], content: Pango.Layout, *, anchor: imutil.Anchor = ...,
  color: Union[RGB, int] = ..., stroke: float = ..., stroke_color: Union[RGB, int] = ...
) -> Image.Image: ...
@overload
def paste(
  im: Image.Image, xy: Tuple[int, int], content: str, font: str, size: float, *,
  anchor: imutil.Anchor = ..., color: Union[RGB, int] = ..., stroke: float = ...,
  stroke_color: Union[RGB, int] = ..., box: Union[Tuple[int, int], int, None] = ...,
  wrap: Wrap = ..., ellipsize: Ellipsize = ..., markup: bool = ..., align: Align = ...,
  spacing: int = ..., lines: int = ...
) -> Image.Image: ...
def paste(
  im: Image.Image, xy: Tuple[int, int], *args, anchor: imutil.Anchor = "lt", **kw
) -> Image.Image:
  text = render(*args, **kw)
  imutil.paste(im, text, xy, anchor=anchor)
  return text
