import json
import re
import time
from io import BytesIO
from pathlib import Path

import nonebot
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import EventMessage
from nonebot.typing import T_State
from PIL import Image, ImageDraw

from util import resources, text

PLUGIN_DIR = Path(__file__).resolve().parent
VIDEO_RE = re.compile(r"av\d{1,9}|(BV|bv)[A-Za-z0-9]{10}")
LINK_RE = re.compile(
  r"bilibili\.com/video/(av\d{1,9}|(BV|bv)[A-Za-z0-9]{10})"
  r"|b23.tv/(av\d{1,9}|BV[A-Za-z0-9]{10}|[A-Za-z0-9]{7})")
INFO_API = "https://api.bilibili.com/x/web-interface/view/detail"
WIDTH = 640
PADDING = 16
CONTENT_WIDTH = WIDTH - PADDING * 2
AVATAR_MARGIN = 8
INFO_MARGIN = 16
INFO_ICON_MARGIN = 4


def normalize_10k(count: int) -> str:
  if count >= 10000:
    return f"{count / 10000:.1f}万"
  else:
    return str(count)


def render_with_icon(icon: str, count: int) -> Image.Image:
  icon_im = Image.open(PLUGIN_DIR / (icon + ".png"))
  text_im = text.render(normalize_10k(count), "sans", 32)
  im = Image.new("RGBA", (
    (icon_im.width + INFO_ICON_MARGIN + text_im.width, max(icon_im.height, text_im.height))))
  im.paste(icon_im, (0, (im.height - icon_im.height) // 2))
  im.paste(text_im, (icon_im.width + INFO_ICON_MARGIN, (im.height - text_im.height) // 2))
  return im


class InfoRender:
  def __init__(self) -> None:
    self.lines: list[list[tuple[Image.Image, int, int]]] = []
    self.height = 0
    self.last_line: list[Image.Image] = []
    self.last_line_width = 0

  def add(self, im: Image.Image) -> None:
    if self.last_line_width + INFO_MARGIN + im.width > CONTENT_WIDTH:
      self.finish_last_line()
    self.last_line.append(im)
    self.last_line_width += INFO_MARGIN + im.width

  def finish_last_line(self) -> None:
    if not self.last_line:
      return
    max_height = max(im.height for im in self.last_line)
    processed_line: list[tuple[Image.Image, int, int]] = []
    x = 0
    for im in self.last_line:
      processed_line.append((im, x, self.height + (max_height - im.height) // 2))
      x += im.width + INFO_MARGIN
    self.lines.append(processed_line)
    self.height += max_height
    self.last_line.clear()
    self.last_line_width = 0

  def render(self, target: Image.Image, x: int, y: int) -> None:
    for line in self.lines:
      for im, offset_x, offset_y in line:
        target.paste(im, (x + offset_x, y + offset_y), im)


async def check_bilibili_link(state: T_State, msg: Message = EventMessage()) -> bool:
  if msg[0].type == "json":
    data = json.loads(msg[0].data["data"])
    try:
      url = data["meta"]["detail_1"]["qqdocurl"]
    except KeyError:
      try:
        url = data["meta"]["news"]["jumpUrl"]
      except KeyError:
        return False
    if match := LINK_RE.search(url):
      state["link"] = match[0]
      return True
    return False
  if match := LINK_RE.search(msg.extract_plain_text()):
    state["link"] = match[0]
    return True
  return False
bilibili_link = nonebot.on_message(check_bilibili_link)


@bilibili_link.handle()
async def handle_bilibili_link(state: T_State) -> None:
  link: str = state["link"]
  http = resources.http()
  match = VIDEO_RE.search(link)
  if not match:
    async with http.get("https://" + link, allow_redirects=False) as response:
      if "Location" not in response.headers:
        return
      link = response.headers["Location"]
    match = VIDEO_RE.search(link)
  if not match:
    return
  video = match[0]
  if video[:2].lower() == "bv":
    url = INFO_API + "?bvid=" + video
  else:
    url = INFO_API + "?aid=" + video[2:]
  async with http.get(url) as response:
    data = await response.json()
  if "data" not in data:
    return
  data_view = data["data"]["View"]
  data_card = data["data"]["Card"]["card"]
  title_im = text.render(
    data_view["title"], "sans", 40, box=CONTENT_WIDTH, mode=text.ELLIPSIZE_END)
  async with http.get(data_card["face"]) as response:
    avatar = Image.open(BytesIO(await response.read()))
  avatar = avatar.convert("RGB").resize((40, 40), Image.BICUBIC)
  circle = Image.new("L", (avatar.width * 2, avatar.height * 2), 0)
  draw = ImageDraw.Draw(circle)
  draw.ellipse((0, 0, circle.width - 1, circle.height - 1), 255)
  avatar.putalpha(circle.resize(avatar.size, Image.BICUBIC))
  fans_im = text.render(normalize_10k(data_card["fans"]) + "粉", "sans", 32)
  name_im = text.render(
    data_card["name"], "sans", 32,
    box=CONTENT_WIDTH - avatar.width - AVATAR_MARGIN * 2 - fans_im.width, mode=text.ELLIPSIZE_END)
  async with http.get(data_view["pic"]) as response:
    cover = Image.open(BytesIO(await response.read()))
  cover = cover.resize((WIDTH, int(cover.height / cover.width * WIDTH)), Image.BICUBIC)
  date = time.strftime("%Y-%m-%d", time.localtime(data_view["pubdate"]))
  infos = InfoRender()
  infos.add(text.render(date, "sans", 32))
  if (parts := data_view["videos"]) > 1:
    infos.add(text.render(f"{parts}P", "sans", 32))
  data_stat = data_view["stat"]
  infos.add(render_with_icon("play", data_stat["view"]))
  infos.add(render_with_icon("danmaku", data_stat["danmaku"]))
  infos.add(render_with_icon("comment", data_stat["reply"]))
  infos.add(render_with_icon("like", data_stat["like"]))
  infos.add(render_with_icon("coin", data_stat["coin"]))
  infos.add(render_with_icon("collect", data_stat["favorite"]))
  infos.add(render_with_icon("share", data_stat["share"]))
  infos.finish_last_line()
  desc = data_view["desc"].replace("\n", " ")
  desc_im = text.render(desc, "sans", 32, box=CONTENT_WIDTH, mode=text.ELLIPSIZE_END)
  name_height = max(avatar.height, name_im.height)
  height = (
    PADDING * 4
    + title_im.height
    + AVATAR_MARGIN
    + name_height
    + cover.height
    + infos.height
    + desc_im.height)
  im = Image.new("RGB", (WIDTH, height), (255, 255, 255))
  y = PADDING
  im.paste(title_im, (PADDING, y), title_im)
  y += title_im.height + AVATAR_MARGIN
  name_y = y + (name_height - name_im.height) // 2
  im.paste(avatar, (PADDING, y + (name_height - avatar.height) // 2), avatar)
  im.paste(name_im, (avatar.width + PADDING + AVATAR_MARGIN, name_y), name_im)
  im.paste(fans_im, (im.width - PADDING - fans_im.width, name_y), fans_im)
  y += name_height + PADDING
  im.paste(cover, (0, y))
  y += cover.height + PADDING
  infos.render(im, PADDING, y)
  y += infos.height
  im.paste(desc_im, (PADDING, y), desc_im)
  f = BytesIO()
  im.save(f, "PNG")
  url = "https://www.bilibili.com/video/" + data_view["bvid"]
  await bilibili_link.finish(MessageSegment.image(f) + url)
