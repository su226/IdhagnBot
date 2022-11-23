from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageOps
from typing_extensions import Self

from util import imutil, textutil

PLUGIN_DIR = Path(__file__).resolve().parent
WIDTH = 640
PADDING = 16
CONTENT_WIDTH = WIDTH - PADDING * 2
AVATAR_MARGIN = 8
INFO_MARGIN = 16
INFO_ICON_MARGIN = 4
ICON_SIZE = 48


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
  def __init__(self, content: str, size: int, lines: int) -> None:
    self.layout = textutil.layout(
      content, "sans", size, box=CONTENT_WIDTH, ellipsize=textutil.ELLIPSIZE_END, lines=lines)
    self.height = self.layout.get_pixel_size().height

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self.height

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    textutil.paste(dst, (x + PADDING, y), self.layout)


class CardLine(Render):
  def __init__(self) -> None:
    pass

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return PADDING * 2 + 2

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    dst.paste((143, 143, 143), (x, y + PADDING, x + WIDTH, y + PADDING + 2))


class CardCover(Render):
  def __init__(self, im: Image.Image, crop: bool = True) -> None:
    if crop:
      self.im = ImageOps.fit(im, (WIDTH, WIDTH * 10 // 16), imutil.scale_resample())
    else:
      self.im = imutil.resize_width(im, WIDTH)

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self.im.height + PADDING * 2

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    dst.paste(self.im, (x, y + PADDING))


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
    self.name_layout = textutil.layout(
      name, "sans", 32, box=name_max, ellipsize=textutil.ELLIPSIZE_END
    )
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
  def __init__(self, content: str) -> None:
    self.layout = textutil.layout(content, "sans", 32)
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
    self.width = ICON_SIZE + INFO_ICON_MARGIN + text_width
    self.height = max(ICON_SIZE, text_height)

  def get_width(self) -> int:
    return self.width

  def get_height(self) -> int:
    return self.height

  def render(self, dst: Image.Image, x: int, y: int):
    icon_im = Image.open(PLUGIN_DIR / (self.icon + ".png"))
    dst.paste(icon_im, (x, y), icon_im)
    textutil.paste(
      dst, (x + ICON_SIZE + INFO_ICON_MARGIN, y + self.height // 2), self.layout, anchor="lm")


class CardInfo(Render):
  def __init__(self) -> None:
    self.lines: List[Tuple[List[Render], int]] = []
    self.height = 0
    self.last_line: List[Render] = []
    self.last_line_width = 0
    self.last_line_height = 0

  def add(self, item: Render) -> None:
    width = item.get_width()
    height = item.get_height()
    if self.last_line:
      self.last_line_width += INFO_MARGIN
    if self.last_line_width + width > CONTENT_WIDTH:
      self.finish_last_line()
    self.last_line.append(item)
    self.last_line_width += width
    self.last_line_height = max(self.last_line_height, height)

  def finish_last_line(self) -> None:
    if not self.last_line:
      return
    self.lines.append((self.last_line, self.last_line_height))
    self.height += self.last_line_height
    self.last_line = []
    self.last_line_width = 0
    self.last_line_height = 0

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self.height

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    for items, height in self.lines:
      x1 = x + PADDING
      for item in items:
        item.render(dst, x1, y + (height - item.get_height()) // 2)
        x1 += item.get_width() + INFO_MARGIN
      y += height


class Card(Render):
  def __init__(self) -> None:
    self.items: List[Render] = []
    self.height = PADDING * 2

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self.height

  def add(self, item: Render) -> Self:
    self.items.append(item)
    self.height += item.get_height()
    return self

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    y += PADDING
    for item in self.items:
      item.render(dst, x, y)
      y += item.get_height()
