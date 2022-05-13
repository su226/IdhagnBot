from typing import Any, cast
from io import BytesIO
import asyncio
import math
import random
import re

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from PIL import Image, ImageDraw, ImageChops
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
import numpy as np

from util import account_aliases

Size = tuple[int, int]
Point = tuple[float, float]
Plane = tuple[Point, Point, Point, Point]
PerspectiveData = tuple[float, float, float, float, float, float, float, float]

def find_coefficients(old_plane: Plane, new_plane: Plane) -> PerspectiveData:
  matrix = []
  for p1, p2 in zip(old_plane, new_plane):
    matrix.append([p2[0], p2[1], 1, 0, 0, 0, -p1[0] * p2[0], -p1[0] * p2[1]])
    matrix.append([0, 0, 0, p2[0], p2[1], 1, -p1[1] * p2[0], -p1[1] * p2[1]])
  a = np.matrix(matrix, dtype=np.float32)
  b = np.array(old_plane).reshape(8)
  res = np.dot(np.linalg.inv(a.T * a) * a.T, b)
  return tuple(np.array(res).reshape(8))

class RemapTransform:
  def __init__(self, old_size: Size, new_plane: Plane, old_plane: Plane | None = None):
    widths = [point[0] for point in new_plane]
    heights = [point[1] for point in new_plane]
    self.old_size = old_size
    self.new_size = (math.ceil(max(widths)), math.ceil(max(heights)))
    if old_plane is None:
      old_plane = ((0, 0), (old_size[0], 0), (old_size[0], old_size[1]), (0, old_size[1]))
    self.data = find_coefficients(old_plane, new_plane)

  def getdata(self) -> tuple[int, tuple[float, ...]]:
    return Image.PERSPECTIVE, self.data

AT_RE = re.compile(r"^\[CQ:at,qq=(\d+)\]$")
LINK_RE = re.compile(r"^https?://.+$")

def try_int(value: str) -> int:
  try:
    return int(value)
  except:
    return 0

async def download_image(url: str, crop: bool) -> Image.Image:
  async with ClientSession() as http:
    response = await http.get(url)
    data = await response.read()
  image = Image.open(BytesIO(data)).convert("RGBA")
  if crop and image.width != image.height:
    new_width = min(image.width, image.height)
    x = (image.width - new_width) // 2
    y = (image.height - new_width) // 2
    image = image.crop((x, y, x + new_width, y + new_width))
  return image

async def get_image_and_user(bot: Bot, event: MessageEvent, pattern: str, default: int, *, crop: bool = True) -> tuple[list[str], None, None] | tuple[None, Image.Image, int | None]:
  if not pattern:
    uid = default
  elif value := try_int(pattern):
    uid = int(value)
  elif match := AT_RE.match(pattern):
    uid = match[1]
  elif match := LINK_RE.match(pattern):
    try:
      return (None, await asyncio.wait_for(download_image(pattern, crop), 10), None)
    except asyncio.TimeoutError:
      return ([f"下载图片超时：{pattern}"], None, None)
    except ClientError:
      return ([f"下载图片失败：{pattern}"], None, None)
    except:
      return ([f"无效图片：{pattern}"], None, None)
  else:
    errors, uid = await account_aliases.match_uid(bot, event, pattern)
    if errors:
      return (errors, None, None)
  try:
    # s 有 100, 160, 640 分别对应最大 3 个尺寸（可以小）和 0 对应原图（不能不填或者自定义）
    return (None, await asyncio.wait_for(download_image(f"https://q1.qlogo.cn/g?b=qq&nk={uid}&s=0", crop), 10), uid)
  except asyncio.TimeoutError:
    return ([f"下载头像超时：{uid}"], None, None)
  except:
    return ([f"下载头像失败：{uid}"], None, None)

def save_transparent_gif(f: Any, frames: list[Image.Image], **kw):
  '''保存GIF动图，保留透明度'''
  p_frames = [frame.convert("P") for frame in frames]
  for i, p_frame in enumerate(p_frames):
    palette = cast(bytes, p_frame.palette.tobytes())
    transparent_index = 0
    for j in range(256):
      if palette[j * 4 + 3] == 0:
        transparent_index = j
        break
    if transparent_index != 0:
      dest = [transparent_index]
      for j in range(transparent_index):
        dest.append(j)
      while len(dest) < 256:
        dest.append(len(dest))
      p_frame = p_frame.remap_palette(dest)
      # 1. remap_palette似乎会把RGBA色板变成RGB色板，把这个色板变回来
      # 2. 把透明色设置成随机颜色，防止遇到黑底头像
      p_frame.putpalette(random.randbytes(3) + b'\0' + palette[:transparent_index * 4] + palette[transparent_index * 4 + 4:], "RGBA")
      p_frames[i] = p_frame
  p_frames[0].save(f, "GIF", append_images=p_frames[1:], save_all=True, loop=0, transparency=0, disposal=2, **kw)

def segment_animated_image(format: str, frames: list[Image.Image], duration: int | list[int]) -> MessageSegment:
  f = BytesIO()
  if format.lower() == "gif":
    if frames[0].mode == "RGBA":
      save_transparent_gif(f, frames, duration=duration)
    else:
      frames[0].save(f, "GIF", append_images=frames[1:], save_all=True, duration=duration, loop=0)
  else:
    frames[0].save(f, format, append_images=frames[1:], save_all=True, duration=duration)
  return MessageSegment.image(f)

def circle(im: Image.Image, antialias: bool = True):
  if antialias:
    mask = Image.new("L", (im.width * 2, im.height * 2))
  else:
    mask = Image.new("L", im.size)
  draw = ImageDraw.Draw(mask)
  draw.ellipse((0, 0, mask.width - 1, mask.height - 1), 255)
  if antialias:
    mask = mask.resize(im.size, Image.ANTIALIAS)
  im.putalpha(ImageChops.multiply(im.getchannel("A"), mask))
