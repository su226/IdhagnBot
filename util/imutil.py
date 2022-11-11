import asyncio
import math
from io import BytesIO
from typing import Generator, Literal, overload

import cairo
from nonebot.adapters.onebot.v11 import MessageSegment
from PIL import Image, ImageChops, ImageDraw, ImageOps

from util import misc

__all__ = [
  "Anchor", "background", "from_cairo", "center_pad", "circle", "contain_down", "frames",
  "get_avatar", "paste", "to_segment", "resize_canvas", "resize_height", "resize_width",
  "sample_frames", "Point", "Plane", "PerspectiveData", "RemapTransform"
]

Anchor = Literal["lt", "lm", "lb", "mt", "mm", "mb", "rt", "rm", "rb"]
Size = tuple[int, int]
Point = tuple[float, float]
Plane = tuple[Point, Point, Point, Point]
PerspectiveData = tuple[float, float, float, float, float, float, float, float]


def resample() -> Image.Resampling:
  return Image.Resampling[misc.CONFIG().resample.upper()]


def scale_resample() -> Image.Resampling:
  return Image.Resampling[misc.CONFIG().scale_resample.upper()]


def circle(im: Image.Image, antialias: bool = True):
  if antialias:
    mask = Image.new("L", (im.width * 2, im.height * 2))
  else:
    mask = Image.new("L", im.size)
  draw = ImageDraw.Draw(mask)
  draw.ellipse((0, 0, mask.width - 1, mask.height - 1), 255)
  if antialias:
    mask = mask.resize(im.size, scale_resample())
  if "A" in im.getbands():
    mask = ImageChops.multiply(im.getchannel("A"), mask)
  im.putalpha(mask)


def from_cairo(surface: cairo.ImageSurface) -> Image.Image:
  w = surface.get_width()
  h = surface.get_height()
  data = surface.get_data()
  if not data:  # 大小为0，data为None
    return Image.new("RGBA", (w, h))
  b, g, r, a = Image.frombytes("RGBa", (w, h), bytes(data)).convert("RGBA").split()
  return Image.merge("RGBA", (r, g, b, a))  # BGRa -> BGRA -> RGBA


def center_pad(im: Image.Image, width: int, height: int) -> Image.Image:
  if im.width > width or im.height > height:
    padded_im = ImageOps.pad(im, (width, height), scale_resample())
  else:
    padded_im = Image.new("RGBA", (width, height))
    padded_im.paste(im, ((width - im.width) // 2, (height - im.height) // 2))
  return padded_im


def resize_canvas(
  im: Image.Image, size: tuple[int, int], center: tuple[float, float] = (0.5, 0.5)
) -> Image.Image:
  x = size[0] - im.width
  y = size[1] - im.height
  l = int(center[0] * x)
  r = x - l
  t = int(center[1] * y)
  b = y - t
  return ImageOps.expand(im, (t, l, r, b))


def square(im: Image.Image) -> Image.Image:
  length = min(im.width, im.height)
  x = (im.width - length) // 2
  y = (im.height - length) // 2
  return im.crop((x, y, x + length, y + length))


def contain_down(im: Image.Image, width: int, height: int) -> Image.Image:
  if im.width > width or im.height > height:
    return ImageOps.contain(im, (width, height), scale_resample())
  return im


def resize_width(im: Image.Image, width: int) -> Image.Image:
  return ImageOps.contain(im, (width, 99999), scale_resample())


def resize_height(im: Image.Image, height: int) -> Image.Image:
  return ImageOps.contain(im, (99999, height), scale_resample())


def background(im: Image.Image, bg: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
  if im.mode == "P" and "A" in im.palette.mode:
    im = im.convert(im.palette.mode)
  if "A" in im.getbands():
    result = Image.new("RGB", im.size, bg)
    result.paste(im, mask=im.getchannel("A"))
    return result
  return im.convert("RGB")


async def get_avatar(
  uid: int, *, raw: bool = False, bg: tuple[int, int, int] | bool = False
) -> Image.Image:
  # s 有 100, 160, 640, 1080 分别对应 4 个最大尺寸（可以小）和 0 对应原图（不能不填或者自定义）
  async with misc.http().get(f"https://q1.qlogo.cn/g?b=qq&nk={uid}&s=0") as response:
    data = await response.read()

  def process() -> Image.Image:
    raw_avatar = Image.open(BytesIO(data))
    if raw:
      return raw_avatar
    if bg is False:
      return raw_avatar.convert("RGBA")
    return background(raw_avatar, (255, 255, 255) if bg is True else bg)
  return await asyncio.to_thread(process)


def frames(im: Image.Image) -> Generator[Image.Image, None, None]:
  if not getattr(im, "is_animated", False):
    yield im
    return
  for i in range(im.n_frames):
    im.seek(i)
    yield im


def sample_frames(im: Image.Image, frametime: int) -> Generator[Image.Image, None, None]:
  if not getattr(im, "is_animated", False):
    while True:
      yield im
  main_pos = 0
  sample_pos = 0
  i = 0
  while True:
    duration = im.info["duration"]
    while sample_pos <= main_pos < sample_pos + duration:
      yield im
      main_pos += frametime
    sample_pos += duration
    i += 1
    if i == im.n_frames:
      i = 0
    im.seek(i)


def paste(
  dst: Image.Image, src: Image.Image, xy: tuple[int, int] = (0, 0),
  mask: Image.Image | None = None, anchor: Anchor = "lt"
) -> None:
  if src.mode == "P" and "A" in src.palette.mode:
    src = src.convert(src.palette.mode)  # RGBA (也可能是LA？)
  if "A" in src.getbands():
    if mask:
      paste_mask = ImageChops.multiply(mask, src.getchannel("A"))
    else:
      paste_mask = src.getchannel("A")
  else:
    paste_mask = mask
  x, y = xy
  xa, ya = anchor
  if xa == "m":
    x -= src.width // 2
  elif xa == "r":
    x -= src.width
  if ya == "m":
    y -= src.height // 2
  elif ya == "b":
    y -= src.height
  dst.paste(src, (x, y), paste_mask)


@overload
def to_segment(
  im: Image.Image | cairo.ImageSurface, *, fmt: str = ..., **kw
) -> MessageSegment: ...
@overload
def to_segment(
  im: list[Image.Image], duration: list[int] | int | Image.Image, *, afmt: str = ..., **kw
) -> MessageSegment: ...
def to_segment(
  im: Image.Image | list[Image.Image] | cairo.ImageSurface,
  duration: list[int] | int | Image.Image = 0, *, fmt: str = "png", afmt: str = "gif", **kw
) -> MessageSegment:
  f = BytesIO()
  if isinstance(im, cairo.ImageSurface):
    im.write_to_png(f)
    return MessageSegment.image(f)
  if isinstance(im, list):
    if len(im) > 1:
      if isinstance(duration, Image.Image):
        d_im = duration
        duration = []
        for i in range(d_im.n_frames):
          d_im.seek(i)
          duration.append(d_im.info["duration"])
      if isinstance(duration, list) and len(duration) != len(im):
        raise ValueError
      if afmt.lower() == "gif":
        # 似乎直接存也可以了？可能是 Pillow 更新了？
        im[0].save(
          f, "GIF", append_images=im[1:], save_all=True, loop=0, disposal=2, duration=duration,
          **kw
        )
      return MessageSegment.image(f)
    im = im[0]
  im.save(f, fmt, **kw)
  return MessageSegment.image(f)


class RemapTransform:
  def __init__(self, old_size: Size, new_plane: Plane, old_plane: Plane | None = None) -> None:
    widths = [point[0] for point in new_plane]
    heights = [point[1] for point in new_plane]
    self.old_size = old_size
    self.new_size = (math.ceil(max(widths)), math.ceil(max(heights)))
    if old_plane is None:
      old_plane = ((0, 0), (old_size[0], 0), (old_size[0], old_size[1]), (0, old_size[1]))
    self.data = self._find_coefficients(old_plane, new_plane)

  def getdata(self) -> tuple[int, tuple[float, ...]]:
    return Image.Transform.PERSPECTIVE, self.data

  @staticmethod
  def _find_coefficients(old_plane: Plane, new_plane: Plane) -> PerspectiveData:
    import numpy as np
    matrix = []
    for p1, p2 in zip(old_plane, new_plane):
      matrix.append([p2[0], p2[1], 1, 0, 0, 0, -p1[0] * p2[0], -p1[0] * p2[1]])
      matrix.append([0, 0, 0, p2[0], p2[1], 1, -p1[1] * p2[0], -p1[1] * p2[1]])
    a = np.array(matrix)
    b = np.array(old_plane).reshape(8)
    res_ = np.linalg.inv(a.T @ a) @ a.T @ b
    return tuple(res_)
