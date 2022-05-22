from collections import defaultdict
from typing import cast

import nonebot
from aiohttp import ClientSession
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot
from pydantic import BaseModel

from util import command, helper
from util.config import BaseConfig

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


class Room(BaseModel):
  id: int
  target: int


class Config(BaseConfig):
  __file__ = "bilibili_live"
  format: str = '''\
[CQ:image,file={cover}]
📺 {username} 开播了 {category}
“{title}”
{link}'''
  interval: int = 60
  rooms: list[Room] = []


CONFIG = Config.load()
API_URL = (
  "https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo?req_biz=link-center")
driver = nonebot.get_driver()
streaming: dict[int, bool] = defaultdict(lambda: False)

check_live = (
  command.CommandBuilder("bilibili_live.check", "检查直播")
  .level("admin")
  .brief("立即检查直播间状态")
  .usage(f'''\
立即检查直播间是否开播
每 {helper.format_time(CONFIG.interval)}会自动检查''')
  .build())


@check_live.handle()
async def handle_check_live():
  if not await check():
    await check_live.send("没有可以推送的内容")


@driver.on_startup
async def on_startup():
  params = []
  for room in CONFIG.rooms:
    params.append(f"&room_ids={room.id}")
  async with ClientSession() as http:
    response = await http.get(API_URL + "".join(params))
    data = await response.json()
  for id, detail in data["data"]["by_room_ids"].items():
    streaming[id] = bool(detail["live_status"])
    status = "已开播" if detail["live_status"] else "未开播"
    logger.debug(f"B站直播: {detail['uname']} -> {status}")


@scheduler.scheduled_job("interval", seconds=CONFIG.interval)
async def check() -> bool:
  params: list[str] = []
  targets: dict[int, int] = {}
  for room in CONFIG.rooms:
    params.append(f"&room_ids={room.id}")
    targets[room.id] = room.target
  async with ClientSession() as http:
    response = await http.get(API_URL + "".join(params))
    data = await response.json()
  bot = cast(Bot, nonebot.get_bot())
  result = False
  for id, detail in data["data"]["by_room_ids"].items():
    status = "已开播" if detail["live_status"] else "未开播"
    logger.debug(f"B站直播: {detail['uname']} -> {status}")
    if not streaming[id] and detail["live_status"]:
      logger.info(f"推送 {detail['uname']} 的直播间")
      await bot.send_group_msg(group_id=targets[int(id)], message=CONFIG.format.format(
        cover=detail["cover"],
        username=detail["uname"],
        category=detail["area_name"],
        title=detail["title"],
        link=detail["live_url"]))
      result = True
    streaming[id] = detail["live_status"]
  return result
