import html
from typing import List, Tuple

from PIL import Image, ImageChops, ImageFilter, ImageOps

from util import imutil, textutil

WIDTH = 640
HEIGHTS = [120, 100, 100, 80]
MIN_LINES = 6


def render(data: List[Tuple[Image.Image, str, str]]) -> Image.Image:
  lines = max(len(data), MIN_LINES)
  if lines < len(HEIGHTS):
    height = sum(HEIGHTS[:lines])
  else:
    height = sum(HEIGHTS) + HEIGHTS[-1] * (lines - len(HEIGHTS))
  im = Image.new("RGB", (WIDTH, height), (17, 17, 17))

  y = 0
  for i in range(lines):
    line_h = HEIGHTS[i if i < len(HEIGHTS) else -1]
    if i % 2:
      im.paste((21, 21, 21), (0, y, WIDTH, y + line_h))
      placeholder_color = (29, 29, 29)
    else:
      placeholder_color = (25, 25, 25)

    im.paste(placeholder_color, (0, y, line_h, y + line_h))
    if i >= len(data):
      textutil.paste(
        im, (line_h // 2, y + line_h // 2), "?", "sans", line_h * 0.5,
        anchor="mm", color=(255, 255, 255),
      )
      textutil.paste(
        im, (round(line_h * 1.2), y + line_h // 2), "虚位以待", "sans", line_h * 0.3,
        anchor="lm", color=(255, 255, 255),
      )
    else:
      avatar, name, info = data[i]
      bg = ImageOps.fit(avatar, (WIDTH - line_h, line_h), imutil.scale_resample())
      bg = bg.filter(ImageFilter.GaussianBlur(8))
      mask = Image.new("L", (2, 1))
      mask.putpixel((0, 0), 64)
      mask.putpixel((1, 0), 8)
      mask = mask.resize(bg.size, imutil.scale_resample())
      bg.putalpha(ImageChops.multiply(bg.getchannel("A"), mask))
      im.paste(bg, (line_h, y), bg)
      avatar = avatar.resize((line_h, line_h), imutil.scale_resample())
      im.paste(avatar, (0, y), avatar)

      name_x = round(line_h * 1.2)
      markup = html.escape(name)
      if info:
        markup += f"\n<span size='66%'>{html.escape(info)}</span>"
      textutil.paste(
        im, (name_x, y + line_h // 2), markup, "sans", line_h * 0.3, anchor="lm", markup=True,
        color=(255, 255, 255), box=WIDTH - name_x - 16, ellipsize="end",
      )

    y += line_h

  return im
