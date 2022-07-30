import asyncio
from io import BytesIO
from typing import Any

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from util import command, context, resources, text

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
  http = resources.http()
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
      time_im = text.render("?", "sans", line_h * 0.5, color=(255, 255, 255))
      text_x = (line_h - time_im.width) // 2
      text_y = y + (line_h - time_im.height) // 2
      im.paste(time_im, (text_x, text_y), time_im)

      time_im = text.render("虚位以待", "sans", line_h * 0.3, color=(255, 255, 255))
      name_x = round(line_h * 1.2)
      name_y = y + (line_h - time_im.height) // 2
      im.paste(time_im, (name_x, name_y), time_im)
    else:
      name, avatar = infos[i]
      bg = ImageOps.fit(avatar, (WIDTH - line_h, line_h), Image.BILINEAR)
      bg = bg.filter(ImageFilter.GaussianBlur(8))
      mask = Image.new("L", (2, 1))
      mask.putpixel((0, 0), 64)
      mask.putpixel((1, 0), 8)
      mask = mask.resize(bg.size, Image.BILINEAR)
      bg.putalpha(ImageChops.multiply(bg.getchannel("A"), mask))
      im.paste(bg, (line_h, y), bg)
      avatar = avatar.resize((line_h, line_h), Image.BILINEAR)
      im.paste(avatar, (0, y), avatar)

      name_x = round(line_h * 1.2)
      name_box = WIDTH - name_x - 16
      name_im = text.render(
        name, "sans", line_h * 0.3, color=(255, 255, 255), box=name_box, mode=text.ELLIPSIZE_END)

      user_data = group_data.get_user(rank[i])
      time_str = user_data.time.strftime("%H:%M:%S")
      time_im = text.render(time_str, "sans", line_h * 0.2, color=(255, 255, 255))

      name_y = y + (line_h - name_im.height - time_im.height) // 2
      im.paste(name_im, (name_x, name_y), name_im)
      im.paste(time_im, (name_x, name_y + name_im.height), time_im)

    y += line_h

  f = BytesIO()
  im.save(f, "PNG")
  await leaderboard.finish(MessageSegment.image(f))
