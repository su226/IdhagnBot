import math
from typing import Any, Dict, Literal, Optional, Tuple, Union, cast, overload

import cairo
import gi
from PIL import Image
from typing_extensions import Self, TypeAlias

from util import colorutil, imutil, misc

gi.require_version("GLib", "2.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import GLib, Pango, PangoCairo  # noqa: E402  # type: ignore

Layout: TypeAlias = Pango.Layout
Wrap = Literal["word", "char", "word_char"]
Ellipsize = Literal[None, "start", "middle", "end"]
Align = Literal["l", "m", "r"]
ImageAlign = Literal["top", "middle", "baseline", "bottom"]
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
ALIGNS: Dict[Align, Pango.Alignment] = {
  "l": Pango.Alignment.LEFT,
  "m": Pango.Alignment.CENTER,
  "r": Pango.Alignment.RIGHT,
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


class RichText:
  _IMAGE_REPLACEMENT = "￼".encode()

  def __init__(self) -> None:
    self._context = Pango.Context()
    self._context.set_font_map(PangoCairo.FontMap.get_default())
    font_options(self._context)
    PangoCairo.context_set_shape_renderer(self._context, self._render_images)
    self._utf8 = bytearray()
    self._attrs = Pango.AttrList()
    self._images: Dict[int, cairo.ImageSurface] = {}
    self._layout = Layout(self._context)
    self._frozen = False

  def _render_images(self, cr: "cairo.Context[Any]", attr: Pango.AttrShape, do_path: bool) -> None:
    if do_path:
      return
    x, y = cr.get_current_point()
    y += attr.ink_rect.y / Pango.SCALE
    surface = self._images[attr.data]
    cr.set_source_surface(surface, x, y)
    cr.rectangle(x, y, surface.get_width(), surface.get_height())
    cr.fill()

  def append(self, text: str) -> Self:
    text = text.replace("\r", "").replace("\n", "\u2028")
    self._utf8.extend(text.encode())
    return self

  def append_markup(self, markup: str) -> Self:
    markup = markup.replace("\r", "").replace("\n", "\u2028")
    _, attrs, text, _ = Pango.parse_markup(markup, -1, "\0")
    utf8 = text.encode()
    self._attrs.splice(attrs, len(self._utf8), len(utf8))
    self._utf8.extend(utf8)
    return self

  def append_image(self, im: Image.Image, align: ImageAlign = "middle") -> Self:
    image_id = id(im)
    if image_id not in self._images:
      self._images[image_id] = imutil.to_cairo(im)
    metrics = self._context.get_metrics(self._layout.get_font_description())
    rect = Pango.Rectangle()
    if align == "top":
      rect.y = -metrics.get_ascent()
    elif align == "middle":
      rect.y = (metrics.get_descent() - metrics.get_ascent() - im.height * Pango.SCALE) // 2
    elif align == "bottom":
      rect.y = -im.height * Pango.SCALE + metrics.get_descent()
    else:
      rect.y = -im.height * Pango.SCALE
    rect.width = im.width * Pango.SCALE
    rect.height = im.height * Pango.SCALE
    attr = Pango.AttrShape.new_with_data(rect, rect, image_id)
    attr.start_index = len(self._utf8)
    attr.end_index = len(self._utf8) + len(self._IMAGE_REPLACEMENT)
    self._utf8.extend(self._IMAGE_REPLACEMENT)
    self._attrs.insert(attr)
    return self

  def set_font(self, font: str, size: float) -> Self:
    if value := misc.CONFIG().font_substitute.get(font, None):
      font = value
    desc = Pango.FontDescription.from_string(font)
    desc.set_absolute_size(Pango.SCALE * size)
    self._layout.set_font_description(desc)
    return self

  def set_width(self, width: int) -> Self:
    self._layout.set_width(width * Pango.SCALE)
    return self

  def set_height(self, height: int) -> Self:
    if height > 0:
      height *= Pango.SCALE
    self._layout.set_height(height)
    return self

  def set_wrap(self, wrap: Wrap) -> Self:
    self._layout.set_wrap(WRAPS[wrap])
    return self

  def set_ellipsize(self, ellipsize: Ellipsize) -> Self:
    self._layout.set_ellipsize(ELLIPSIZES[ellipsize])
    return self

  def set_spacing(self, spacing: float) -> Self:
    if spacing < 0:
      self._layout.set_line_spacing(spacing)
      self._layout.set_spacing(0)
    else:
      self._layout.set_line_spacing(0)
      self._layout.set_spacing(spacing * Pango.SCALE)
    return self

  def set_align(self, align: Align) -> Self:
    self._layout.set_alignment(ALIGNS[align])
    return self

  def size(self) -> Tuple[int, int]:
    _, rect = self._layout.get_pixel_extents()
    return rect

  def unwrap(self) -> Layout:
    self._layout.set_text(self._utf8.decode())
    self._layout.set_attributes(self._attrs)
    return self._layout

  def render(
    self, color: imutil.Color = (0, 0, 0), stroke: float = 0,
    stroke_color: imutil.Color = (255, 255, 255)
  ) -> Image.Image:
    return render(self.unwrap(), color=color, stroke=stroke, stroke_color=stroke_color)

  def paste(
    self, im: Image.Image, xy: Tuple[float, float], anchor: imutil.Anchor = "lt",
    color: imutil.Color = (0, 0, 0), stroke: float = 0,
    stroke_color: imutil.Color = (255, 255, 255)
  ) -> Image.Image:
    src = render(self.unwrap(), color=color, stroke=stroke, stroke_color=stroke_color)
    imutil.paste(im, src, xy, anchor=anchor)
    return src


def escape(text: str) -> str:
  return GLib.markup_escape_text(text, -1)


def special_font(name: str, fallback: str) -> str:
  if value := misc.CONFIG().special_font.get(name, None):
    return value
  return fallback


def font_options(
  context: Union[None, Pango.Context, "cairo.Context[Any]"] = None
) -> cairo.FontOptions:
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
  content: str, font: str, size: float, *, box: Optional[int] = None, wrap: Wrap = "word",
  ellipsize: Ellipsize = None, markup: bool = False, align: Align = "l", spacing: int = 0,
  lines: int = 0
) -> Layout:
  render = RichText().set_font(font, size).set_wrap(wrap).set_align(align).set_spacing(spacing)
  if box:
    render.set_width(box)
  if lines:
    render.set_height(-lines).set_ellipsize(ellipsize)
  if markup:
    try:
      render.append_markup(content)
    except GLib.Error:
      render.append(content)
  else:
    render.append(content)
  return render.unwrap()


@overload
def render(
  content: Layout, *, color: imutil.Color = ..., stroke: float = ...,
  stroke_color: imutil.Color = ...
) -> Image.Image: ...
@overload
def render(
  content: str, font: str, size: float, *, color: imutil.Color = ..., stroke: float = ...,
  stroke_color: imutil.Color = ..., box: Optional[int] = ..., wrap: Wrap = ...,
  ellipsize: Ellipsize = ..., markup: bool = ..., align: Align = ..., spacing: int = ...,
  lines: int = ...
) -> Image.Image: ...
def render(
  content: Union[str, Layout], *args: Any, color: imutil.Color = (0, 0, 0), stroke: float = 0,
  stroke_color: imutil.Color = (255, 255, 255), **kw: Any
) -> Image.Image:
  if isinstance(content, Layout):
    l = cast(Layout, content)
  else:
    l = layout(content, *args, **kw)
  _, rect = l.get_pixel_extents()
  margin = math.ceil(stroke)
  x = -rect.x + margin
  y = -rect.y + margin
  w = rect.width + margin * 2
  h = rect.height + margin * 2
  with cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h) as surface:
    cr = cairo.Context(surface)
    if stroke:
      if isinstance(stroke_color, int):
        stroke_color = colorutil.split_rgb(stroke_color)
      cr.move_to(x, y)
      PangoCairo.layout_path(cr, l)
      cr.set_line_width(stroke * 2)
      cr.set_source_rgb(stroke_color[0] / 255, stroke_color[1] / 255, stroke_color[2] / 255)
      cr.stroke()
    if isinstance(color, int):
      color = colorutil.split_rgb(color)
    cr.move_to(x, y)
    cr.set_source_rgb(color[0] / 255, color[1] / 255, color[2] / 255)
    PangoCairo.show_layout(cr, l)
    return imutil.from_cairo(surface)


@overload
def paste(
  im: Image.Image, xy: Tuple[float, float], content: Layout, *, anchor: imutil.Anchor = ...,
  color: imutil.Color = ..., stroke: float = ..., stroke_color: imutil.Color = ...
) -> Image.Image: ...
@overload
def paste(
  im: Image.Image, xy: Tuple[float, float], content: str, font: str, size: float, *,
  anchor: imutil.Anchor = ..., color: imutil.Color = ..., stroke: float = ...,
  stroke_color: imutil.Color = ..., box: Optional[int] = ..., wrap: Wrap = ...,
  ellipsize: Ellipsize = ..., markup: bool = ..., align: Align = ..., spacing: int = ...,
  lines: int = ...
) -> Image.Image: ...
def paste(
  im: Image.Image, xy: Tuple[float, float], *args: Any, anchor: imutil.Anchor = "lt", **kw: Any
) -> Image.Image:
  text = render(*args, **kw)
  imutil.paste(im, text, xy, anchor=anchor)
  return text
