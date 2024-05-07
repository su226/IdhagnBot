import asyncio
import math
from datetime import date, timedelta
from typing import List

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.typing import T_State
from PIL import Image, ImageOps
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, desc, func, select

from util import colorutil, configs, context, imutil, misc, record, textutil
from util.command import CommandBuilder
from util.dateutil import DATE_ARGS_USAGE, parse_date_range_args
from util.material_color import source_color_from_image
from util.material_color.hct import Hct


class Config(BaseModel):
  leaderboard_limit: int = 20

CONFIG = configs.SharedConfig("charts", Config)


group_statistics = (
  CommandBuilder("charts.statistics.group", "群统计", "统计")
  .brief("查看最近的个人发言数")
  .usage('''\
/群统计 - 查看最近30天的发言数，以天为单位
/群统计 年 - 查看最近一年的发言数，以月为单位''')
  .in_group()
  .state(is_user=False)
  .build()
)
personal_statistics = (
  CommandBuilder("charts.statistics.personal", "个人统计", "我的统计")
  .brief("查看最近的个人发言数")
  .usage('''\
/个人统计 - 查看最近30天的发言数，以天为单位
/个人统计 年 - 查看最近一年的发言数，以月为单位
/个人统计 GitHub - 查看最近一年的发言数，GitHub风格''')
  .state(is_user=True)
  .build()
)
@group_statistics.handle()
@personal_statistics.handle()
async def handle_statistics(
  bot: Bot, event: MessageEvent, state: T_State, arg: Message = CommandArg(),
) -> None:
  group_id = context.get_event_context(event)
  user_id = event.user_id
  style = arg.extract_plain_text().rstrip().lower()
  if style == "年":
    style = "year"
  elif style == "github":
    style = "github"
  else:
    style = "month"
  is_user = state["is_user"]

  today = date.today()
  if style == "year":
    date_func = func.date(record.Received.time, "start of month")
    if today.month == 12:
      begin_time = date(today.year, 1, 1)
    else:
      begin_time = date(today.year - 1, today.month + 1, 1)
  elif style == "github":
    date_func = func.date(record.Received.time)
    begin_time = today - timedelta(today.weekday() + 52 * 7)
  else:
    date_func = func.date(record.Received.time)
    begin_time = today - timedelta(31)
  async with AsyncSession(record.engine) as session:
    query = select(
      date_func,
      func.count(date_func),
    )
    if group_id != -1:
      query = query.where(record.Received.group_id == group_id)
    if is_user:
      query = query.where(record.Received.user_id == user_id)
    result = await session.execute(
      query
      .where(record.Received.time >= begin_time)
      .group_by(date_func),
    )
    result = result.all()

  title = f"{'月' if style == 'month' else '年'}发言数"
  if is_user:
    if group_id != -1:
      name, group, avatar = await asyncio.gather(
        context.get_card_or_name(bot, group_id, user_id),
        bot.get_group_info(group_id=group_id),
        imutil.get_avatar(user_id),
      )
      title = f"{name} 在 {group['group_name']} 群内的{title}"
    else:
      name, avatar = await asyncio.gather(
        context.get_card_or_name(bot, group_id, user_id),
        imutil.get_avatar(user_id),
      )
      title = f"{name} 的{title}"
  else:
    group, avatar = await asyncio.gather(
      bot.get_group_info(group_id=group_id),
      imutil.get_avatar(gid=group_id),
    )
    title = f"{group['group_name']} 群内的{title}"

  def make_github() -> MessageSegment:
    mon_im = textutil.render("周一", "sans", 24)
    thu_im = textutil.render("周四", "sans", 24)
    sun_im = textutil.render("周日", "sans", 24)
    weekdays_w = max(mon_im.width, thu_im.width, sun_im.width) + 16
    width = weekdays_w + 53 * 30
    title_im = textutil.render(title, "sans", 24, box=width - 16, align="m")
    months_im = [textutil.render(month, "sans", 24) for month in [
      "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月",
      "十二月",
    ]]
    months_h = max(im.height for im in months_im)
    header_h = title_im.height + months_h
    maxcount = max(count for _, count in result)
    min_im = textutil.render("0", "sans", 24)
    max_im = textutil.render(str(maxcount), "sans", 24)
    minmax_h = max(22, min_im.height, max_im.height)
    im = Image.new("RGB", (
      width, header_h + 7 * 30 + minmax_h + 8,
    ), (255, 255, 255))
    imutil.paste(im, title_im, (im.width / 2, 0), anchor="mt")
    imutil.paste(im, mon_im, (weekdays_w - 8, header_h + 11), anchor="rm")
    imutil.paste(im, thu_im, (weekdays_w - 8, header_h + 30 * 3 + 11), anchor="rm")
    imutil.paste(im, sun_im, (weekdays_w - 8, header_h + 30 * 6 + 11), anchor="rm")
    hct = Hct.from_argb(source_color_from_image(avatar.resize((64, 64), Image.Resampling.LANCZOS)))
    color1 = colorutil.split_rgb(int(Hct(hct.hue, max(hct.chroma, 48), 70)))
    color2 = (235, 237, 240)
    x = im.width - 8
    y = im.height - 8 - minmax_h / 2
    imutil.paste(im, max_im, (x, y), anchor="rm")
    x -= max_im.width + 8
    for i in range(4, -1, -1):
      imutil.paste(im, (colorutil.blend(color1, color2, i / 4), (22, 22)), (x, y), anchor="rm")
      x -= 30
    imutil.paste(im, min_im, (x, y), anchor="rm")
    curtime = begin_time
    prevtime = curtime
    i = 0
    j = 0
    while curtime <= today:
      if i < len(result) and result[i][0] == str(curtime):
        count = result[i][1]
        i += 1
      else:
        count = 0
      x, y = divmod(j, 7)
      x = weekdays_w + x * 30
      y = header_h + y * 30
      if curtime.month != prevtime.month:
        month_im = months_im[curtime.month - 1]
        if x + month_im.width > im.width - 8:
          imutil.paste(im, month_im, (x + 22, header_h), anchor="rb")
        else:
          imutil.paste(im, month_im, (x, header_h), anchor="lb")
      im.paste(colorutil.blend(color1, color2, count / maxcount), (x, y, x + 22, y + 22))
      prevtime = curtime
      curtime += timedelta(1)
      j += 1
    return imutil.to_segment(im)

  def make() -> MessageSegment:
    palette = BarPalette(avatar)
    labels_im: List[Image.Image] = []
    counts: List[int] = []
    i = 0
    curtime = begin_time
    while curtime <= today:
      labels_im.append(textutil.render(
        curtime.strftime("%m-%d" if style == "month" else "%Y-%m"),
        "sans", 32, color=palette.fg,
      ).transpose(Image.Transpose.ROTATE_90))
      if i < len(result) and result[i][0] == str(curtime):
        counts.append(result[i][1])
        i += 1
      else:
        counts.append(0)
      if style == "month":
        curtime += timedelta(1)
      else:
        if curtime.month == 12:
          curtime = date(curtime.year + 1, 1, 1)
        else:
          curtime = curtime.replace(month=curtime.month + 1)
    counts_im = [
      textutil.render(str(count), "sans", 32, color=palette.fg)
      .transpose(Image.Transpose.ROTATE_90)
      for count in counts
    ]
    max_count = max(max(counts), 1)
    bar_gap = math.ceil(max_count / 10)
    axis = [
      (count, textutil.render(str(count), "sans", 32, color=palette.fg))
      for count in range(bar_gap, max_count + 1, bar_gap)
    ]
    axis_w = max(im.width for _, im in axis) + 32
    bar_w = 96 if style == "year" else 64
    chart_w = bar_w * len(counts)
    width = axis_w + chart_w
    bar_hmax = 960 - max(im.height for im in counts_im) - 32
    heights = [bar_hmax * count // max_count for count in counts]
    title_im = textutil.render(title, "sans", 32, box=width - 16, align="m")
    header_h = title_im.height + 16
    im = Image.new("RGB", (width, header_h + 960), (255, 255, 255))
    imutil.paste(im, title_im, (im.width / 2, 8), anchor="mt")
    bg2 = palette[93]
    im.paste(palette.bg, (0, header_h, axis_w, header_h + 960))
    for i, height in enumerate(heights):
      bg = bg2 if i % 2 == 0 else palette.bg
      x = axis_w + i * bar_w
      im.paste(bg, (x, header_h, x + bar_w, header_h + 960 - height))
    line_im = Image.new("RGBA", (chart_w, 2), (0, 0, 0, 31))
    for count, count_im in axis:
      y = header_h + 960 - bar_hmax * count // max_count
      im.paste(line_im, (axis_w, y - 1), line_im)
      imutil.paste(im, count_im, (axis_w - 16, y), anchor="rm")
    fg2 = palette[67]
    for i, (height, label_im, count_im) in enumerate(zip(heights, labels_im, counts_im)):
      fg = fg2 if i % 2 == 0 else palette.bar
      x = i * bar_w + axis_w
      im.paste(fg, (x, header_h + 960 - height, x + bar_w, header_h + 960))
      imutil.paste(im, label_im, (x + bar_w / 2, header_h + 960 - 16), anchor="mb")
      imutil.paste(
        im, count_im, (x + bar_w / 2, header_h + 960 - max(height, label_im.height + 16) - 16),
        anchor="mb",
      )
    return imutil.to_segment(im)

  if style == "github":
    fn = make_github
  else:
    fn = make

  await Matcher.finish(await misc.to_thread(fn))


class BarPalette:
  def __init__(self, im: Image.Image) -> None:
    hct = Hct.from_argb(source_color_from_image(im))
    self.hue = hct.hue
    self.chroma = max(48, hct.chroma)
    self.fg = self[40]
    self.bar = self[70]
    self.bg = self[95]

  def __getitem__(self, tone: int) -> colorutil.RGB:
    return colorutil.split_rgb(int(Hct(self.hue, self.chroma, tone)))


leaderboard = (
  CommandBuilder("charts.leaderboard", "排行", "排名")
  .brief("查看最近的发言排行")
  .usage(DATE_ARGS_USAGE)
  .in_group()
  .build()
)
@leaderboard.handle()
async def handle_leaderboard(bot: Bot, event: MessageEvent, arg: Message = CommandArg()) -> None:
  start_datetime, end_datetime = await parse_date_range_args(arg)
  config = CONFIG()
  group_id = context.get_event_context(event)

  async with AsyncSession(record.engine) as session:
    result = await session.execute(
      select(
        record.Received.user_id,
        count_func := func.count(col(record.Received.user_id)),
      )
      .group_by(col(record.Received.user_id))
      .where(
        record.Received.group_id == group_id,
        record.Received.time >= start_datetime,
        record.Received.time < end_datetime,
      )
      .order_by(desc(count_func))
      .limit(config.leaderboard_limit),
    )
    result = result.all()
  if not result:
    await leaderboard.finish((
      f"{start_datetime:%Y-%m-%d %H:%M:%S} 到 {end_datetime:%Y-%m-%d %H:%M:%S} 内没有数据"
    ))

  names, avatars, group = await asyncio.gather(
    asyncio.gather(*(context.get_card_or_name(bot, event, uid) for uid, _ in result)),
    asyncio.gather(*(imutil.get_avatar(uid, bg=True) for uid, _ in result)),
    bot.get_group_info(group_id=group_id),
  )
  end_datetime -= timedelta(seconds=1)  # 显示 23:59:59 而不是 00:00:00，以防误会

  def make() -> MessageSegment:
    nonlocal avatars
    avatars = [ImageOps.fit(avatar, (64, 64), Image.Resampling.LANCZOS) for avatar in avatars]
    palettes = [BarPalette(avatar) for avatar in avatars]
    counts_im = [
      textutil.render(str(count), "sans", 32, color=palette.fg)
      for (_, count), palette in zip(result, palettes)
    ]
    chart_h = len(names) * 64
    header_im = textutil.render(
      f"{group['group_name']}\n"
      f"{start_datetime:%Y-%m-%d %H:%M:%S} 到 {end_datetime:%Y-%m-%d %H:%M:%S} 的排行",
      "sans", 32, align="m",
    )
    header_h = header_im.height + 16
    max_count = max(result[0][1], 1)
    line_gap = math.ceil(max_count / 10)
    footers = [
      (count, textutil.render(str(count), "sans", 32))
      for count in range(line_gap, max_count + 1, line_gap)
    ]
    footer_h = max(im.height for _, im in footers) + 8
    im = Image.new("RGB", (1280, header_h + chart_h + footer_h), (255, 255, 255))
    imutil.paste(im, header_im, (im.width / 2, 8), anchor="mt")
    bar_wmax = im.width - 96 - max(im.width for im in counts_im)
    widths = [count * bar_wmax // max_count for (_, count) in result]
    for i, (width, palette) in enumerate(zip(widths, palettes)):
      y = i * 64 + header_h
      im.paste(palette.bg, (64 + width, y, im.width, y + 64))
    line_im = Image.new("RGBA", (2, chart_h), (0, 0, 0, 31))
    for count, count_im in footers:
      x = 64 + count * bar_wmax // max_count
      im.paste(line_im, (x - 1, header_h), line_im)
      imutil.paste(im, count_im, (x, header_h + chart_h), anchor="mt")
    infos = zip(widths, counts_im, avatars, palettes, names)
    for i, (width, count_im, avatar, palette, name) in enumerate(infos):
      y = i * 64 + header_h
      im.paste(avatar, (0, y))
      im.paste(palette.bar, (64, y, 64 + width, y + 64))
      name_im = textutil.paste(
        im, (80, y + 32), name, "sans", 32,
        color=palette.fg, box=im.width - 112 - count_im.width, ellipsize="end", anchor="lm",
      )
      imutil.paste(im, count_im, (max(width, name_im.width + 16) + 80, y + 32), anchor="lm")
    return imutil.to_segment(im)

  await leaderboard.finish(await misc.to_thread(make))
