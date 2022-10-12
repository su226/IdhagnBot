import asyncio
import math
import re
from io import BytesIO
from typing import Any, Generator

import aiohttp
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from PIL import Image, ImagePalette

from util import account_aliases, util

Size = tuple[int, int]
Point = tuple[float, float]
Plane = tuple[Point, Point, Point, Point]
PerspectiveData = tuple[float, float, float, float, float, float, float, float]


def find_coefficients(old_plane: Plane, new_plane: Plane) -> PerspectiveData:
  import numpy as np
  matrix = []
  for p1, p2 in zip(old_plane, new_plane):
    matrix.append([p2[0], p2[1], 1, 0, 0, 0, -p1[0] * p2[0], -p1[0] * p2[1]])
    matrix.append([0, 0, 0, p2[0], p2[1], 1, -p1[1] * p2[0], -p1[1] * p2[1]])
  a = np.array(matrix)
  b = np.array(old_plane).reshape(8)
  res_ = np.linalg.inv(a.T @ a) @ a.T @ b
  return tuple(res_)


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
    return Image.Transform.PERSPECTIVE, self.data


AT_RE = re.compile(r"^\[CQ:at,qq=(\d+)\]$")
LINK_RE = re.compile(r"^https?://.+$")
IMAGE_RE = re.compile(r"^\[CQ:image[^\]]+\]$")


async def download_image(url: str, *, crop: bool = True, raw: bool = False) -> Image.Image:
  async with util.http().get(url) as response:
    image = Image.open(BytesIO(await response.read()))
  if raw:
    return image
  if crop and image.width != image.height:
    new_width = min(image.width, image.height)
    x = (image.width - new_width) // 2
    y = (image.height - new_width) // 2
    image = image.crop((x, y, x + new_width, y + new_width))
  return image.convert("RGBA")


async def get_image_from_link(url: str, **kw) -> Image.Image:
  try:
    return await asyncio.wait_for(download_image(url, **kw), 10)
  except asyncio.TimeoutError as e:
    raise util.AggregateError(f"下载图片超时：{url}") from e
  except aiohttp.ClientError as e:
    raise util.AggregateError(f"下载图片失败：{url}") from e
  except Exception as e:
    raise util.AggregateError(f"无效图片：{url}") from e


async def get_avatar(uid: int, *, crop: bool = True, raw: bool = False) -> Image.Image:
  try:
    return await asyncio.wait_for(util.get_avatar(uid, raw=raw), 10)
  except asyncio.TimeoutError:
    # 以防有笨b（其实是我自己）眼瞎，这里的错误信息和上面的不一样
    raise util.AggregateError(f"下载头像超时：{uid}")
  except aiohttp.ClientError:
    raise util.AggregateError(f"下载头像失败：{uid}")


async def get_image_and_user(
  bot: Bot, event: MessageEvent, pattern: str, default: int, **kw
) -> tuple[Image.Image, int | None]:
  if pattern in ("-", "发送"):
    await bot.send(event, "请发送一张图片")
    pattern = str(await util.prompt(event)).strip()
  if not pattern:
    uid = default
  elif match := AT_RE.match(pattern):
    uid = int(match[1])
  elif IMAGE_RE.match(pattern):
    return await get_image_from_link(Message(pattern)[0].data["url"], **kw), None
  elif match := LINK_RE.match(pattern):
    return await get_image_from_link(pattern, **kw), None
  elif pattern in ("~", "自己"):
    uid = event.user_id
  elif pattern in ("0", "机器人"):
    uid = event.self_id
  elif pattern in ("?", "回复"):
    if not event.reply:
      raise util.AggregateError("没有回复")
    uid = event.reply.sender.user_id
    if not uid:
      raise util.AggregateError("没有回复")
  else:
    uid = await account_aliases.match_uid(bot, event, pattern)
  return await get_avatar(uid, **kw), uid


def save_transparent_gif(f: Any, frames: list[Image.Image], **kw):
  '''保存GIF动图，保留透明度'''
  p_frames = [frame.convert("P") for frame in frames]
  for frame in p_frames:
    palette: ImagePalette.ImagePalette = frame.palette
    if palette.mode != "RGBA":
      continue
    data = palette.tobytes()
    for j in range(256):
      if data[j * 4 + 3] == 0:
        frame.info["transparency"] = j
        break
  p_frames[0].save(f, "GIF", append_images=p_frames[1:], save_all=True, loop=0, disposal=2, **kw)


def segment_animated_image(
  format: str, frames: list[Image.Image], duration: int | list[int]
) -> MessageSegment:
  f = BytesIO()
  if format.lower() == "gif":
    save_transparent_gif(f, frames, duration=duration)
  else:
    frames[0].save(f, format, append_images=frames[1:], save_all=True, duration=duration)
  return MessageSegment.image(f)


def frames(im: Image.Image) -> Generator[Image.Image, None, None]:
  if not getattr(im, "is_animated", False):
    yield im
    return
  for i in range(im.n_frames):
    im.seek(i)
    yield im
