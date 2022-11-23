import json
import re
import time
from io import BytesIO

import nonebot
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import EventMessage
from nonebot.typing import T_State
from PIL import Image

from util import imutil, misc
from util.images.card import Card, CardAuthor, CardCover, CardInfo, CardText, InfoCount, InfoText

VIDEO_RE = re.compile(r"av\d{1,9}|(BV|bv)[A-Za-z0-9]{10}")
LINK_RE = re.compile(
  r"bilibili\.com/video/(av\d{1,9}|(BV|bv)[A-Za-z0-9]{10})"
  r"|b23\.tv/(av\d{1,9}|BV[A-Za-z0-9]{10}|[A-Za-z0-9]{7})")
INFO_API = "https://api.bilibili.com/x/web-interface/view/detail"


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
  http = misc.http()

  # 1. 获取真实链接（如果是b23.tv短链接）
  link = state["link"]
  match = VIDEO_RE.search(link)
  if not match:
    async with http.get("https://" + link, allow_redirects=False) as response:
      match = VIDEO_RE.search(response.headers.get("Location", ""))
      if not match:
        return

  # 2. 获取视频信息、封面、UP主头像
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
  data_stat = data_view["stat"]

  async with http.get(data_card["face"]) as response:
    avatar_data = await response.read()
  async with http.get(data_view["pic"]) as response:
    cover_data = await response.read()

  # 3. 构建卡片
  def make() -> MessageSegment:
    avatar = Image.open(BytesIO(avatar_data))
    cover = Image.open(BytesIO(cover_data))
    card = Card()
    card.add(CardText(data_view["title"], 40, 2))
    card.add(CardAuthor(avatar, data_card["name"], data_card["fans"]))
    card.add(CardCover(cover))

    infos = CardInfo()
    date = time.strftime("%Y-%m-%d", time.localtime(data_view["pubdate"]))
    infos.add(InfoText(date))
    if (parts := data_view["videos"]) > 1:
      infos.add(InfoText(f"{parts}P"))
    infos.add(InfoCount("play", data_stat["view"]))
    infos.add(InfoCount("danmaku", data_stat["danmaku"]))
    infos.add(InfoCount("comment", data_stat["reply"]))
    infos.add(InfoCount("like", data_stat["like"]))
    infos.add(InfoCount("coin", data_stat["coin"]))
    infos.add(InfoCount("collect", data_stat["favorite"]))
    infos.add(InfoCount("share", data_stat["share"]))
    infos.finish_last_line()
    card.add(infos)

    desc = data_view["desc"]
    if desc and desc != "-":
      card.add(CardText(desc, 32, 3))

    # 4. 渲染卡片并发送
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return imutil.to_segment(im)

  url = "https://www.bilibili.com/video/" + data_view["bvid"]
  await bilibili_link.finish(await misc.to_thread(make) + url)
