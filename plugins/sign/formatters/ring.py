import asyncio
import calendar
import math
from datetime import date

import cairo
from nonebot.adapters.onebot.v11 import Bot, Message
from PIL import ImageEnhance, ImageFilter

from util import context, currency, imutil, misc, textutil

from ..config import STATE, FormatData


def rounded_rect(cr: cairo.Context, x1: float, y1: float, x2: float, y2: float, r: float) -> None:
  cr.move_to(x1 + r, y1)
  cr.line_to(x2 - r, y1)
  cr.arc(x2 - r, y1 + r, r, math.pi / 4 * 3, math.pi * 2)
  cr.line_to(x2, y2 - r)
  cr.arc(x2 - r, y2 - r, r, 0, math.pi / 2)
  cr.line_to(x1 + r, y2)
  cr.arc(x1 + r, y2 - r, r, math.pi / 2, math.pi)
  cr.line_to(x1, y1 + r)
  cr.arc(x1 + r, y1 + r, r, math.pi, math.pi / 4 * 3)


BOX_H = 160
BOX_MARGIN = 50
BOX_PADDING = 8


async def get_hitokoto() -> str:
  http = misc.http()
  async with http.get("https://v1.hitokoto.cn/") as response:
    data = await response.json()
    return data["hitokoto"]


async def format(bot: Bot, format_data: FormatData) -> Message:
  avatar, name, hitokoto = await asyncio.gather(
    imutil.get_avatar(format_data.uid, bg=(255, 255, 255)),
    context.get_card_or_name(bot, format_data.gid, format_data.uid),
    get_hitokoto()
  )

  def make() -> Message:
    nonlocal avatar
    group_data = STATE(format_data.gid)
    user_data = group_data.get_user(format_data.uid)

    im = avatar.resize((640, 640), imutil.scale_resample())
    im = im.filter(ImageFilter.GaussianBlur(8))
    im = ImageEnhance.Brightness(im).enhance(0.5)
    center_x = im.width // 2
    avatar_y = (im.height - BOX_MARGIN - BOX_H) // 2

    with cairo.ImageSurface(cairo.FORMAT_ARGB32, im.width, im.height) as surface:
      cr = cairo.Context(surface)
      textutil.font_options(cr)
      today = date.today()
      _, days = calendar.monthrange(today.year, today.month)
      angle = math.pi / days * 0.9
      for i in range(days):
        pos = i / days * math.pi * 2 - math.pi / 2
        cr.new_path()
        if i + 1 in user_data.calendar:
          cr.set_source_rgb(1, 1, 1)
        else:
          cr.set_source_rgba(1, 1, 1, 0.2)
        cr.set_line_width(4)
        cr.arc(center_x, avatar_y, 134, pos - angle, pos + angle)
        cr.stroke()
        cr.translate(center_x + math.cos(pos) * 140, avatar_y + math.sin(pos) * 140)
        cr.rotate(pos + math.pi / 2)
        s = str(i + 1)
        cr.set_font_size(16)
        cr.move_to(-cr.text_extents(s).x_advance / 2, 0)
        cr.show_text(s)
        cr.identity_matrix()
      box_y2 = im.height - BOX_MARGIN
      y = box_y2 - BOX_H
      rounded_rect(cr, BOX_MARGIN, y, im.width - BOX_MARGIN, box_y2, 24)
      cr.set_source_rgba(0, 0, 0, 0.2)
      cr.fill()
      overlay = imutil.from_cairo(surface)
    im.paste(overlay, mask=overlay)

    avatar = avatar.resize((256, 256), imutil.scale_resample())
    imutil.circle(avatar)
    imutil.paste(im, avatar, (center_x, avatar_y), anchor="mm")

    y += BOX_PADDING
    box_w = im.width - BOX_MARGIN * 2
    content_w = box_w - BOX_PADDING * 2

    y += textutil.paste(
      im, (center_x, y), name, "sans bold", 28,
      anchor="mt", box=content_w, ellipsize="middle", color=(255, 255, 255)
    ).height

    rank = group_data.rank.index(format_data.uid) + 1
    if format_data.coin == -1:
      s = f"#{rank} 已经签到过了"
    else:
      s = f"#{rank} 签到成功"
    y += textutil.paste(
      im, (center_x, y), s, "sans", 24, anchor="mt", box=box_w, color=(255, 255, 255)
    ).height

    coin = currency.get_coin(format_data.gid, format_data.uid)
    s = f"连续{user_data.combo_days + 1}天 总计{user_data.total_days}天 {coin}金币"
    if format_data.coin != -1:
      s += f"(+{format_data.coin})"
    y += textutil.paste(
      im, (center_x, y), s, "sans", 24, anchor="mt", box=box_w, color=(255, 255, 255)
    ).height

    hitokoto_h = box_y2 - BOX_PADDING - y
    text_im = textutil.render(hitokoto, "sans", 20, color=(255, 255, 255))
    text_im = imutil.contain_down(text_im, content_w, hitokoto_h)
    imutil.paste(im, text_im, (center_x, y + hitokoto_h // 2), anchor="mm")

    return Message(imutil.to_segment(im))

  return await misc.to_thread(make)
