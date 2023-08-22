from pathlib import Path
from typing import Any, List, Optional, Tuple, Union, cast, overload

from PIL import Image, ImageOps
from typing_extensions import Self

from util import imutil, textutil

Color = Tuple[int, int, int]
PLUGIN_DIR = Path(__file__).resolve().parent
WIDTH = 640
PADDING = 16
CONTENT_WIDTH = WIDTH - PADDING * 2
AVATAR_MARGIN = 8
INFO_MARGIN = 16
INFO_ICON_MARGIN = 4
INFO_ICON_SIZE = 48
DIM_COLOR = (224, 224, 224)


def normalize_10k(count: int) -> str:
  if count >= 10000:
    return f"{count / 10000:.1f}万"
  else:
    return str(count)


class Render:
  def get_width(self) -> int:
    raise NotImplementedError

  def get_height(self) -> int:
    raise NotImplementedError

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    pass


class CardText(Render):
  @overload
  def __init__(
    self, content: textutil.Layout, *, color: imutil.Color = ..., stroke: float = ...,
    stroke_color: imutil.Color = ...
  ) -> None: ...

  @overload
  def __init__(
    self, content: str, font: str = ..., size: float = ..., *, color: imutil.Color = ...,
    stroke: float = ..., stroke_color: imutil.Color = ..., wrap: textutil.Wrap = ...,
    ellipsize: textutil.Ellipsize = ..., markup: bool = ..., align: textutil.Align = ...,
    spacing: int = ..., lines: int = ...
  ) -> None: ...

  def __init__(
    self, content: Union[textutil.Layout, str], font: str = "sans-serif", size: float = 32,
    *args: Any, color: imutil.Color = (0, 0, 0), stroke: float = 0,
    ellipsize: textutil.Ellipsize = "end", stroke_color: imutil.Color = (255, 255, 255), **kw: Any
  ) -> None:
    self.layout = (
      cast(textutil.Layout, content) if isinstance(content, textutil.Layout) else
      textutil.layout(content, font, size, *args, box=CONTENT_WIDTH, ellipsize=ellipsize, **kw)
    )
    self.width, self.height = self.layout.get_pixel_size()
    self.color = color
    self.stroke = stroke
    self.stroke_color = stroke_color

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self.height

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    textutil.paste(
      dst, (x + PADDING, y), self.layout, color=self.color, stroke=self.stroke,
      stroke_color=self.stroke_color
    )


class CardLine(Render):
  def __init__(self) -> None:
    pass

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return 2

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    dst.paste(DIM_COLOR, (x, y, x + WIDTH, y + 2))


class CardCover(Render):
  def __init__(self, im: Image.Image, crop: bool = True) -> None:
    if crop:
      self.im = ImageOps.fit(im, (WIDTH, WIDTH * 10 // 16), imutil.scale_resample())
    else:
      self.im = imutil.resize_width(im, WIDTH)

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self.im.height

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    dst.paste(self.im, (x, y))


class CardAuthor(Render):
  def __init__(self, avatar: Image.Image, name: str, fans: int = -1) -> None:
    self.avatar = avatar.convert("RGB").resize((40, 40), imutil.scale_resample())
    imutil.circle(self.avatar)
    name_max = CONTENT_WIDTH - self.avatar.width - AVATAR_MARGIN
    self.height = self.avatar.height
    if fans != -1:
      self.fans_layout = textutil.layout(normalize_10k(fans) + "粉", "sans", 32)
      fans_width, fans_height = self.fans_layout.get_pixel_size()
      name_max -= AVATAR_MARGIN + fans_width
      self.height = max(self.height, fans_height)
    else:
      self.fans_layout = None
    self.name_layout = textutil.layout(name, "sans", 32, box=name_max, ellipsize="end")
    name_height = self.name_layout.get_pixel_size().height
    self.height = max(self.height, name_height)

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self.height

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    dst.paste(self.avatar, (x + PADDING, y + (self.height - self.avatar.height) // 2), self.avatar)
    y += self.height // 2
    name_x = PADDING + self.avatar.width + AVATAR_MARGIN
    textutil.paste(dst, (x + name_x, y), self.name_layout, anchor="lm")
    if self.fans_layout is not None:
      textutil.paste(dst, (x + WIDTH - PADDING, y), self.fans_layout, anchor="rm")


class InfoText(Render):
  def __init__(self, content: str, size: int = 32) -> None:
    self.layout = textutil.layout(content, "sans", size)
    self.width, self.height = self.layout.get_pixel_size()

  def get_width(self) -> int:
    return self.width

  def get_height(self) -> int:
    return self.height

  def render(self, dst: Image.Image, x: int, y: int):
    textutil.paste(dst, (x, y), self.layout)


class InfoCount(Render):
  def __init__(self, icon: str, count: int) -> None:
    self.icon = icon
    self.layout = textutil.layout(normalize_10k(count), "sans", 32)
    text_width, text_height = self.layout.get_pixel_size()
    self.width = INFO_ICON_SIZE + INFO_ICON_MARGIN + text_width
    self.height = max(INFO_ICON_SIZE, text_height)

  def get_width(self) -> int:
    return self.width

  def get_height(self) -> int:
    return self.height

  def render(self, dst: Image.Image, x: int, y: int):
    icon_im = Image.open(PLUGIN_DIR / (self.icon + ".png"))
    dst.paste(icon_im, (x, y), icon_im)
    textutil.paste(
      dst, (x + INFO_ICON_SIZE + INFO_ICON_MARGIN, y + self.height // 2), self.layout, anchor="lm"
    )


class CardInfo(Render):
  def __init__(self, gap_x: int = INFO_MARGIN, gap_y: int = 0) -> None:
    self.lines: List[Tuple[List[Render], int]] = []
    self.height = 0
    self.last_line: List[Render] = []
    self.last_line_width = 0
    self.last_line_height = 0
    self.gap_x = gap_x
    self.gap_y = gap_y

  def add(self, item: Render) -> None:
    width = item.get_width()
    height = item.get_height()
    if self.last_line:
      self.last_line_width += self.gap_x
    if self.last_line_width + width > CONTENT_WIDTH:
      self._push_line()
    self.last_line.append(item)
    self.last_line_width += width
    self.last_line_height = max(self.last_line_height, height)

  def _push_line(self) -> None:
    if self.lines:
      self.height += self.gap_y
    self.lines.append((self.last_line, self.last_line_height))
    self.height += self.last_line_height
    self.last_line = []
    self.last_line_width = 0
    self.last_line_height = 0

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    height = self.height + self.last_line_height
    if self.lines and self.last_line:
      height += self.gap_y
    return height

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    for items, height in self.lines:
      x1 = x + PADDING
      for item in items:
        item.render(dst, x1, y + (height - item.get_height()) // 2)
        x1 += item.get_width() + self.gap_x
      y += height + self.gap_y
    x1 = x + PADDING
    for item in self.last_line:
      item.render(dst, x1, y + (self.last_line_height - item.get_height()) // 2)
      x1 += item.get_width() + self.gap_x


class CardMargin(Render):
  def __init__(self, margin: int = PADDING) -> None:
    self.margin = margin

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self.margin

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    pass


class CardTab(Render):
  def __init__(
    self, content: str = "", title: str = "", icon: Optional[Image.Image] = None
  ) -> None:
    self.icon = icon
    box = CONTENT_WIDTH - 8
    self.title_im = textutil.render(title, "sans", 32, box=box) if title else None
    if icon:
      box -= icon.width + PADDING
    self.content_im = (
      textutil.render(content, "sans", 32, box=box, markup=True) if content else None
    )

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    title_h = self.title_im.height if self.title_im else 0
    content_h = self.content_im.height if self.content_im else 0
    if self.icon:
      content_h = max(content_h, self.icon.height)
    return title_h + content_h + 16

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    x += PADDING
    if self.title_im:
      dst.paste(DIM_COLOR, (x, y, x + self.title_im.width + 16, y + self.title_im.height))
      dst.paste(self.title_im, (x + 8, y), self.title_im)
      y += self.title_im.height
    content_h = self.content_im.height if self.content_im else 0
    if self.icon:
      content_h = max(content_h, self.icon.height)
    dst.paste(DIM_COLOR, (x, y, WIDTH - PADDING, y + content_h + 16))
    x += 8
    y_ = y + 8 + content_h / 2
    if self.icon:
      imutil.paste(dst, self.icon, (x, y_), anchor="lm")
      x += self.icon.width + PADDING
    if self.content_im:
      imutil.paste(dst, self.content_im, (x, y_), anchor="lm")


class Card(Render):
  def __init__(self, padding: int = PADDING, gap: int = 0) -> None:
    self.items: List[Render] = []
    self.padding = padding
    self.gap = gap
    self.height = padding * 2

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self.height

  def add(self, item: Render) -> Self:
    if self.items:
      self.height += self.gap
    self.items.append(item)
    self.height += item.get_height()
    return self

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    y += self.padding
    for item in self.items:
      item.render(dst, x, y)
      y += item.get_height() + self.gap
