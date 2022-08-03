import asyncio
import html
from io import BytesIO
from typing import Any

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from util import command, context, text, util

from .config import STATE

WIDTH = 640
HEIGHTS = [140, 120, 100, 80]
MIN_LINES = 5


# 草，走，忽略
leaderboard = (
  command.CommandBuilder("sign.leaderboard", "签到排名", "签到排行")
  .in_group()
  .brief("查看签到排名")
  .build())


@leaderboard.handle()
async def handle_leaderboard(bot: Bot, event: MessageEvent) -> None:
  async def fetch_avatar(uid: int) -> Image.Image:
    async with http.get(f"https://q1.qlogo.cn/g?b=qq&nk={uid}&s=0") as response:
      data = await response.read()
    im = Image.open(BytesIO(data)).convert("RGBA")
    return im

  async def fetch_data(uid: int) -> tuple[str, Image.Image]:
    return await asyncio.gather(context.get_card_or_name(bot, event, uid), fetch_avatar(uid))

  gid = context.get_event_context(event)
  group_data = STATE(gid)
  group_data.update()
  rank = group_data.rank
  http = util.http()
  infos: list[tuple[str, Image.Image]] = await asyncio.gather(*(fetch_data(uid) for uid in rank))

  lines = max(len(infos), MIN_LINES)
  height = sum(HEIGHTS) + HEIGHTS[-1] * (lines - len(HEIGHTS))
  im = Image.new("RGB", (WIDTH, height), (17, 17, 17))
  draw = ImageDraw.Draw(im)

  y = 0
  for i in range(lines):
    line_h = HEIGHTS[i if i < len(HEIGHTS) else -1]
    if i % 2:
      draw.rectangle((0, y, WIDTH - 1, y + line_h - 1), (21, 21, 21))
      placeholder_color = (29, 29, 29)
    else:
      placeholder_color = (25, 25, 25)

    draw.rectangle((0, y, line_h - 1, y + line_h - 1), placeholder_color)
    if i >= len(rank):
      text.paste(
        im, (line_h // 2, y + line_h // 2), "?", "sans", line_h * 0.5,
        anchor="mm", color=(255, 255, 255))
      text.paste(
        im, (round(line_h * 1.2), y + line_h // 2), "虚位以待", "sans", line_h * 0.3,
        anchor="lm", color=(255, 255, 255))
    else:
      name, avatar = infos[i]
      bg = ImageOps.fit(avatar, (WIDTH - line_h, line_h), util.scale_resample)
      bg = bg.filter(ImageFilter.GaussianBlur(8))
      mask = Image.new("L", (2, 1))
      mask.putpixel((0, 0), 64)
      mask.putpixel((1, 0), 8)
      mask = mask.resize(bg.size, util.scale_resample)
      bg.putalpha(ImageChops.multiply(bg.getchannel("A"), mask))
      im.paste(bg, (line_h, y), bg)
      avatar = avatar.resize((line_h, line_h), util.scale_resample)
      im.paste(avatar, (0, y), avatar)

      name_x = round(line_h * 1.2)
      user_data = group_data.get_user(rank[i])
      markup = f"{html.escape(name)}\n<span size='66%'>{user_data.time:%H:%M:%S}</span>"
      text.paste(
        im, (name_x, y + line_h // 2), markup, "sans", line_h * 0.3, anchor="lm", markup=True,
        color=(255, 255, 255), box=WIDTH - name_x - 16, mode=text.ELLIPSIZE_END)

    y += line_h

  f = BytesIO()
  im.save(f, "PNG")
  await leaderboard.finish(MessageSegment.image(f))
