import asyncio
import time
from collections import defaultdict
from io import BytesIO
from typing import cast

import nonebot
from apscheduler.schedulers.base import JobLookupError
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from PIL import Image
from pydantic import BaseModel

from util import command, configs, imutil, misc
from util.images.card import Card, CardAuthor, CardCover, CardText

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


class GroupTarget(BaseModel):
  group: int


class UserTarget(BaseModel):
  user: int


class User(BaseModel):
  uid: int
  targets: list[GroupTarget | UserTarget]


class Config(BaseModel):
  interval: int = 10
  users: list[User] = []


CONFIG = configs.SharedConfig("bilibili_live", Config)
# https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo?req_biz=link-center&room_ids=
API_URL = "https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids"
INFO_API_URL = "https://api.live.bilibili.com/live_user/v1/Master/info"
driver = nonebot.get_driver()
streaming: dict[int, bool] = defaultdict(lambda: False)


@CONFIG.onload()
def onload(prev: Config | None, curr: Config) -> None:
  async def prepare() -> None:
    params = []
    for user in curr.users:
      params.append(f"uids[]={user.uid}")
    http = misc.http()
    async with http.get(API_URL + "?" + "&".join(params)) as response:
      data = await response.json()
    for uid, detail in data["data"].items():
      streaming[uid] = current = bool(detail["live_status"])
      status = "已开播" if current else "未开播"
      logger.debug(f"B站直播: {detail['uname']} -> {status}")
    scheduler.add_job(check, "interval", id="bilibili_live", replace_existing=True, seconds=10)

  try:
    scheduler.remove_job("bilibili_live")
  except JobLookupError:
    pass
  if curr.users:
    asyncio.create_task(prepare())


def check_live_usage() -> str:
  return f'''\
立即检查直播间是否开播
每 {misc.format_time(CONFIG().interval)}会自动检查'''
check_live = (
  command.CommandBuilder("bilibili_live.check", "检查直播")
  .level("admin")
  .brief("立即检查直播间状态")
  .usage(check_live_usage)
  .build()
)
@check_live.handle()
async def handle_check_live():
  if not await check():
    await check_live.finish("没有可以推送的内容")


@driver.on_startup
async def on_startup() -> None:
  CONFIG()


async def get_message(data: dict) -> Message:
  http = misc.http()
  async with http.get(f"{INFO_API_URL}?uid={data['uid']}") as response:
    info = await response.json()
    fans: int = info["data"]["follower_num"]
    desc: str = info["data"]["room_news"]["content"]
  async with http.get(data["face"]) as response:
    avatar_data = await response.read()
  async with http.get(data["cover_from_user"]) as response:
    cover_data = await response.read()
  category = f"{data['area_v2_parent_name']} - {data['area_v2_name']}"

  def make() -> MessageSegment:
    avatar = Image.open(BytesIO(avatar_data))
    cover = Image.open(BytesIO(cover_data))
    card = Card()
    card.add(CardText(data["title"], 40, 2))
    card.add(CardText(category, 32, 1))
    card.add(CardAuthor(avatar, data["uname"], fans))
    card.add(CardCover(cover))
    card.add(CardText(desc, 32, 3))

    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return imutil.to_segment(im)

  url = f"https://live.bilibili.com/{data['room_id']}"
  return f"{data['uname']} 开播了 {category}" + await asyncio.to_thread(make) + url


async def check() -> bool:
  total_t = time.perf_counter()

  prepare_t = time.perf_counter()
  try:
    bot = cast(Bot, nonebot.get_bot())
  except ValueError:
    return False
  params: list[str] = []
  targets: dict[int, list[GroupTarget | UserTarget]] = {}
  for user in CONFIG().users:
    params.append(f"uids[]={user.uid}")
    targets[user.uid] = user.targets
  prepare_t = time.perf_counter() - prepare_t

  fetch_t = time.perf_counter()
  http = misc.http()
  async with http.get(API_URL + "?" + "&".join(params)) as response:
    data = await response.json()
  fetch_t = time.perf_counter() - fetch_t

  send_t = time.perf_counter()
  result = False
  for uid, detail in data["data"].items():
    current = bool(detail["live_status"])
    status = "已开播" if current else "未开播"
    logger.debug(f"B站直播: {detail['uname']} -> {status}")
    if not streaming[uid] and current:
      logger.info(f"推送 {detail['uname']} 的直播间")
      message = await get_message(detail)
      for target in targets[int(uid)]:
        if isinstance(target, GroupTarget):
          await bot.send_group_msg(group_id=target.group, message=message)
        else:
          await bot.send_private_msg(user_id=target.user, message=message)
      result = True
    streaming[uid] = current
  send_t = time.perf_counter() - send_t

  total_t = time.perf_counter() - total_t
  if total_t > 10:
    logger.warning(
      f"检查直播时间过长，请检查网络: \n"
      f"准备 {prepare_t:.3f}s\n获取 {fetch_t:.3f}s\n发送 {send_t:.3f}s"
    )
  return result
