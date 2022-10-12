import asyncio
import html
from calendar import Calendar
from datetime import date
from io import BytesIO
from typing import Any

from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from PIL import Image

from util import currency, text, util

from ..config import CONFIG, STATE, FormatData

MONTHS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]


async def make_image(bot: Bot, format_data: FormatData) -> MessageSegment:
  async def get_user_infos(users: list[int]) -> dict[int, dict[str, Any]]:
    coros = [bot.get_group_member_info(group_id=format_data.gid, user_id=user) for user in users]
    return dict(zip(users, await asyncio.gather(*coros)))

  # 排行
  config = CONFIG()
  group_data = STATE(format_data.gid)
  infos = await get_user_infos(group_data.rank)
  segments = ["<big>今日排名</big>"]
  for i, user in enumerate(group_data.rank):
    name = infos[user]["card"] or infos[user]["nickname"]
    if i < len(config.first_prefix):
      prefix = config.first_prefix[i]
    else:
      prefix = f"{i + 1}. "
    name = html.escape(name)
    if user == format_data.uid:
      name = f"<b>{name}</b>"
    time = group_data.users[user].time.strftime("%H:%M:%S")
    segments.append(f"{prefix}{name} - {time}")
  rank_im = text.render("\n".join(segments), "sans", 32, markup=True)

  today = date.today()
  weeks = Calendar().monthdayscalendar(today.year, today.month)
  im = Image.new(
    "RGB", (656 + rank_im.width, max(264 + len(weeks) * 80, rank_im.height + 64)), (255, 255, 255))
  im.paste(rank_im, (624, 32), rank_im)

  # 头像
  avatar = await util.get_avatar(format_data.uid)
  avatar = avatar.resize((96, 96), util.scale_resample)
  util.circle(avatar)
  im.paste(avatar, (32, 32), avatar)

  # 用户名
  text.paste(
    im, (152, 32), infos[format_data.uid]["card"] or infos[format_data.uid]["nickname"],
    "sans", 32, box=336, ellipsize=text.ELLIPSIZE_END)

  # 群名
  text.paste(
    im, (152, 80), (await bot.get_group_info(group_id=format_data.gid))["group_name"], "sans", 28,
    color=(143, 143, 143))

  # 月份
  text.paste(
    im, (584, 32), MONTHS[today.month - 1] + "月", "sans", 38, color=(0, 0, 0), anchor="rt")

  # 日历头
  for x, weekday in enumerate(WEEKDAYS):
    text.paste(
      im, (32 + x * 80 + 40, 152 + 40), weekday, "sans", 28, color=(143, 143, 143), anchor="mm")

  # 日历
  user_data = group_data.get_user(format_data.uid)
  circle = Image.new("RGB", (72, 72), (76, 175, 80))
  util.circle(circle)
  for y, days in enumerate(weeks):
    for x, day in enumerate(days):
      if day == 0:
        continue
      elif day in user_data.calendar:
        im.paste(circle, (32 + x * 80 + 4, 232 + y * 80 + 4), circle)
        color = (255, 255, 255)
      else:
        color = (0, 0, 0)
      text.paste(
        im, (32 + x * 80 + 40, 232 + y * 80 + 40), str(day), "sans", 28, color=color, anchor="mm")

  f = BytesIO()
  im.save(f, "PNG")
  return MessageSegment.image(f)


async def format(bot: Bot, format_data: FormatData) -> Message:
  group_data = STATE(format_data.gid)
  user_data = group_data.get_user(format_data.uid)
  image = await make_image(bot, format_data)
  coin = currency.get_coin(format_data.gid, format_data.uid)
  if format_data.coin == -1:
    return f"今天你已经签到过了\n你目前有{coin}个金币" + image

  segments = [f"签到成功，获得{format_data.coin}个金币，共有{coin}个金币"]
  if format_data.combo_bonus:
    segments.append(f"连签加成：{round(format_data.combo_bonus * 100)}%")
  if format_data.rank_bonus:
    segments.append(f"排名加成：{round(format_data.rank_bonus * 100)}%")
  rank = group_data.rank.index(format_data.uid)
  segments.append(
    f"今日排名第{rank + 1}，"
    f"连续签到{user_data.combo_days + 1}天，"
    f"总计签到{user_data.total_days}天")
  return "\n".join(segments) + image
