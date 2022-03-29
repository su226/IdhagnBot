from collections import defaultdict
from typing import cast
from aiohttp import ClientSession
from util.config import BaseModel, BaseConfig
from apscheduler.schedulers.base import BaseScheduler
from util import context
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot
import nonebot

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

def format_duration(seconds: int) -> str:
  minutes, seconds = divmod(seconds, 60)
  hours,   minutes = divmod(minutes, 60)
  days,    hours   = divmod(hours, 24)
  segments = []
  if days:
    segments.append(f"{days} 天")
  if hours:
    segments.append(f"{hours} 时")
  if minutes:
    segments.append(f"{minutes} 分")
  if seconds:
    segments.append(f"{seconds} 秒")
  return " ".join(segments)

config = Config.load()
scheduler: BaseScheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler
driver = nonebot.get_driver()
API_URL = "https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo?req_biz=link-center"
streaming: dict[int, bool] = defaultdict(lambda: False)

check_live = nonebot.on_command("检查直播", permission=context.Permission.ADMIN)
check_live.__cmd__ = "检查直播"
check_live.__brief__ = "立即检查直播间状态"
check_live.__usage__ = f'''\
立即检查直播间是否开播
每 {format_duration(config.interval)}会自动检查'''
check_live.__perm__ = context.Permission.ADMIN
@check_live.handle()
async def handle_check_live():
  await check()
  await check_live.send("检查直播间完成")

@driver.on_startup
async def on_startup():
  params = []
  for room in config.rooms:
    params.append(f"&room_ids={room.id}")
  async with ClientSession() as http:
    response = await http.get(API_URL + "".join(params))
    data = await response.json()
  for id, detail in data["data"]["by_room_ids"].items():
    streaming[id] = bool(detail["live_status"])
    status = "已开播" if detail["live_status"] else "未开播"
    logger.debug(f"B站直播: {detail['uname']} -> {status}")

@scheduler.scheduled_job("interval", seconds=config.interval)
async def check():
  params: list[str] = []
  targets: dict[int, int] = {}
  for room in config.rooms:
    params.append(f"&room_ids={room.id}")
    targets[room.id] = room.target
  async with ClientSession() as http:
    response = await http.get(API_URL + "".join(params))
    data = await response.json()
  bot = cast(Bot, nonebot.get_bot())
  for id, detail in data["data"]["by_room_ids"].items():
    status = "已开播" if detail["live_status"] else "未开播"
    logger.debug(f"B站直播: {detail['uname']} -> {status}")
    if not streaming[id] and detail["live_status"]:
      logger.info(f"推送 {detail['uname']} 的直播间")
      await bot.send_group_msg(group_id=targets[int(id)], message=config.format.format(
        cover=detail["cover"],
        username=detail["uname"],
        category=detail["area_name"],
        title=detail["title"],
        link=detail["live_url"]))
    streaming[id] = detail["live_status"]
