import json
import re
import time
from io import BytesIO
from typing import Any, Dict, Generator, Tuple

import nonebot
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent, MessageSegment
from nonebot.params import EventMessage
from nonebot.typing import T_State
from PIL import Image

from util import context, imutil, misc, permission
from util.api_common import bilibili_auth
from util.images.card import Card, CardAuthor, CardCover, CardInfo, CardText, InfoCount, InfoText

VIDEO_RE = re.compile(r"av\d{1,9}|(BV|bv)[A-Za-z0-9]{10}")
LINK_RE = re.compile(
  r"bilibili\.com/video/(av\d{1,9}|(BV|bv)[A-Za-z0-9]{10})"
  r"|b23\.tv/(av\d{1,9}|BV[A-Za-z0-9]{10}|[A-Za-z0-9]{7})",
)
INFO_API = "https://api.bilibili.com/x/web-interface/view/detail"
ParseRequest = Tuple[str, str, int]
last_videos: Dict[int, ParseRequest] = {}


def is_link_alike(last: ParseRequest, link: str) -> bool:
  '''
  检查两次解析请求是否相似
  当本次解析的链接与上一次相同或包含上一次解析出的 BV 号 / AV 号时
  判定为解析请求相似，避免再次发送结果
  '''
  last_link, last_bvid, last_aid = last
  if last_link == link:
    return True
  if match := VIDEO_RE.search(link):
    video = match[0]
    if video[:2] == "av":
      return int(video[2:]) == last_aid
    else:
      return video[2:] == last_bvid
  return False


def extract_bilibili_links(msg: Message) -> Generator[str, Any, Any]:
  '''提取消息中所有的可能是 B 站视频的链接，视频不一定有效，提取出的 b23.tv 短链也不一定指向视频'''
  for seg in msg:
    if seg.type == "json":
      data = json.loads(seg.data["data"])
      try:
        url = data["meta"]["detail_1"]["qqdocurl"]
      except KeyError:
        try:
          url = data["meta"]["news"]["jumpUrl"]
        except KeyError:
          continue
      if match := LINK_RE.search(url):
        yield match[0]
    elif seg.type == "text":
      yield from (match[0] for match in LINK_RE.finditer(seg.data["text"]))


def format_duration(seconds: int) -> str:
  minutes, seconds = divmod(seconds, 60)
  hours, minutes = divmod(minutes, 24)
  if hours:
    return f"{hours}:{minutes:02}:{seconds:02}"
  return f"{minutes:02}:{seconds:02}"


async def check_bilibili_link(
  event: MessageEvent, state: T_State, msg: Message = EventMessage(),
) -> bool:
  http = misc.http()
  first_valid = None
  link_count = 0
  if isinstance(event, GroupMessageEvent):
    last_video = last_videos.get(event.group_id, None)
  else:
    last_video = None

  for link in extract_bilibili_links(msg):
    # 不包括上一次发送过的链接，防止群内有多个机器人时刷屏
    if last_video and is_link_alike(last_video, link):
      continue
    link_count += 1
    # 此处只是为了验证是否有多于一个链接，因此如果已有视频数据则只统计数量
    if first_valid is not None:
      if link_count > 1:
        break
      continue

    if match := VIDEO_RE.search(link):
      video = match[0]
    else:
      # 获取真实链接（如果是b23.tv短链接）
      async with http.get("https://" + link, allow_redirects=False) as response:
        if match := VIDEO_RE.search(response.headers.get("Location", "")):
          video = match[0]
        else:
          continue

    if video[:2] == "av":
      params = {"aid": video[2:]}
    else:
      params = {"bvid": video}
    async with http.get(
      INFO_API,
      headers={"User-Agent": misc.BROWSER_UA},
      params=params,
    ) as response:
      data = await response.json()
    if data["code"] not in (-404, 62002, 62004):  # 不存在、不可见、审核中
      first_valid = link, bilibili_auth.ApiError.check(data)

  if first_valid is not None:
    link, data = first_valid
    if isinstance(event, GroupMessageEvent):
      last_videos[event.group_id] = (link, data["View"]["bvid"][2:], data["View"]["aid"])
    state["data"] = data
    state["more"] = link_count > 1
    return True

  return False

bilibili_link = nonebot.on_message(
  check_bilibili_link,
  context.build_permission(("bilibili_link",), permission.Level.MEMBER),
)

@bilibili_link.handle()
async def handle_bilibili_link(event: MessageEvent, state: T_State) -> None:
  http = misc.http()

  # 1. 获取视频信息、封面、UP主头像
  data = state["data"]
  data_view = data["View"]
  data_card = data["Card"]["card"]
  data_stat = data_view["stat"]

  async with http.get(data_card["face"]) as response:
    avatar_data = await response.read()
  async with http.get(data_view["pic"]) as response:
    cover_data = await response.read()

  def make() -> MessageSegment:
    # 2. 构建卡片
    card = Card(0)

    block = Card()
    block.add(CardText(data_view["title"], size=40, lines=2))
    avatar = Image.open(BytesIO(avatar_data))
    block.add(CardAuthor(avatar, data_card["name"], data_card["fans"]))
    card.add(block)

    cover = Image.open(BytesIO(cover_data))
    card.add(CardCover(cover))

    block = Card()
    infos = CardInfo()
    date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data_view["pubdate"]))
    infos.add(InfoText(date))
    infos.add(InfoText("转载" if data_view["copyright"] == 2 else "自制"))
    duration = format_duration(data_view["duration"])
    if (parts := data_view["videos"]) > 1:
      duration = f"{parts}P共{duration}"
    infos.add(InfoText(duration))
    infos.add(InfoCount("play", data_stat["view"]))
    infos.add(InfoCount("danmaku", data_stat["danmaku"]))
    infos.add(InfoCount("comment", data_stat["reply"]))
    infos.add(InfoCount("like", data_stat["like"]))
    infos.add(InfoCount("coin", data_stat["coin"]))
    infos.add(InfoCount("collect", data_stat["favorite"]))
    infos.add(InfoCount("share", data_stat["share"]))
    block.add(infos)
    desc = data_view["desc"]
    if desc and desc != "-":
      block.add(CardText(desc, size=28, lines=3, color=(102, 102, 102)))
    if tags := data["Tags"]:
      infos = CardInfo(8)
      for tag in tags:
        if tag["tag_type"] != "bgm":
          infos.add(InfoText("#" + tag["tag_name"], 26))
      block.add(infos)
    card.add(block)

    # 3. 渲染卡片并发送
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return imutil.to_segment(im)

  info = f"https://www.bilibili.com/video/{data_view['bvid']} (av{data_view['aid']})"
  if state["more"]:
    info += "\n⚠发现多个链接，结果仅包含第一个有效视频"
  await bilibili_link.finish(await misc.to_thread(make) + info)
