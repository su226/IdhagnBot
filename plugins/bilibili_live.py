import asyncio
import time
from collections import defaultdict
from io import BytesIO
from typing import Any, Awaitable, Dict, List, Optional, Union, cast

import nonebot
from apscheduler.schedulers.base import JobLookupError
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg
from PIL import Image
from pydantic import BaseModel

from util import command, configs, context, imutil, misc
from util.images.card import Card, CardAuthor, CardCover, CardText

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402


class GroupTarget(BaseModel):
  group: int

  async def send(self, bot: Bot, message: Message) -> None:
    await bot.send_group_msg(group_id=self.group, message=message)


class UserTarget(BaseModel):
  user: int

  async def send(self, bot: Bot, message: Message) -> None:
    await bot.send_private_msg(user_id=self.user, message=message)


Target = Union[GroupTarget, UserTarget]
class User(BaseModel):
  uid: int
  targets: List[Target]


class Config(BaseModel):
  interval: int = 10
  users: List[User] = []


CONFIG = configs.SharedConfig("bilibili_live", Config)
# https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo?req_biz=link-center&room_ids=
API_URL = "https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids"
INFO_API_URL = "https://api.live.bilibili.com/live_user/v1/Master/info"
driver = nonebot.get_driver()
streaming: Dict[int, bool] = defaultdict(lambda: False)


@CONFIG.onload()
def onload(prev: Optional[Config], curr: Config) -> None:
  async def prepare() -> None:
    params = []
    for user in curr.users:
      params.append(f"uids[]={user.uid}")
    http = misc.http()
    async with http.get(API_URL + "?" + "&".join(params)) as response:
      data = await response.json()
    for uid, detail in data["data"].items():
      streaming[uid] = current = detail["live_status"] == 1  # 0下播 1直播 2轮播
      status = "已开播" if current else "未开播"
      logger.debug(f"B站直播: {detail['uname']} -> {status}")
    scheduler.add_job(check, "interval", id="bilibili_live", replace_existing=True, seconds=10)

  try:
    scheduler.remove_job("bilibili_live")
  except JobLookupError:
    pass
  if curr.users:
    try:
      asyncio.get_running_loop().create_task(prepare())
    except RuntimeError:
      pass  # 否则没法用 --export-html


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


force_push = (
  command.CommandBuilder("bilibili_live.force_push", "推送直播")
  .level("admin")
  .brief("强制推送B站直播")
  .usage("/推送直播 <UID>")
  .build()
)
@force_push.handle()
async def handle_force_push(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
  try:
    uid = int(arg.extract_plain_text())
  except ValueError:
    await force_push.finish(force_push.__doc__)
  http = misc.http()
  async with http.get(API_URL + f"?uids[]={uid}") as response:
    data = await response.json()
  if not data["data"]:
    await force_push.finish("无法获取这个用户的直播间")
  message = await get_message(data["data"][str(uid)])
  ctx = context.get_event_context(event)
  real_ctx = getattr(event, "group_id", -1)
  if ctx != real_ctx:
    await bot.send_group_msg(group_id=ctx, message=message)
    name = context.CONFIG().groups[ctx]._name
    await force_push.finish(f"已推送到 {name}")
  else:
    await force_push.finish(Message(message))


@driver.on_startup
async def on_startup() -> None:
  CONFIG()


async def get_message(data: Dict[str, Any]) -> Message:
  http = misc.http()
  async with http.get(f"{INFO_API_URL}?uid={data['uid']}") as response:
    info = await response.json()
    fans: int = info["data"]["follower_num"]
    desc: str = info["data"]["room_news"]["content"]
  async with http.get(data["face"]) as response:
    avatar_data = await response.read()
  if (cover_url := data["cover_from_user"]):
    async with http.get(cover_url) as response:
      cover_data = await response.read()
  else:
    cover_data = None
  category = f"{data['area_v2_parent_name']} - {data['area_v2_name']}"

  def make() -> MessageSegment:
    card = Card(0)
    block = Card()
    block.add(CardText(data["title"], size=40, lines=2))
    block.add(CardText(category, size=32, lines=1))
    avatar = Image.open(BytesIO(avatar_data))
    block.add(CardAuthor(avatar, data["uname"], fans))
    card.add(block)
    if cover_data:
      cover = Image.open(BytesIO(cover_data))
    else:
      cover = avatar
    card.add(CardCover(cover))
    if desc:
      block = Card()
      block.add(CardText(desc, size=32, lines=3))
      card.add(block)

    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return imutil.to_segment(im)

  url = f"https://live.bilibili.com/{data['room_id']}"
  return Message([
    MessageSegment.text(f"{data['uname']} 开播了 {category}"),
    await misc.to_thread(make),
    MessageSegment.text(url),
  ])


async def push_all(bot: Bot, data: Dict[str, Any], targets: List[Target]) -> None:
  logger.info(f"推送 {data['uname']} 的直播间")
  try:
    message = await get_message(data)
  except Exception:
    logger.exception(f"获取 {data['uname']} 的直播间的推送消息失败")
    return

  async def send_with_except(target: Target, message: Message) -> None:
    try:
      await target.send(bot, message)
    except ActionFailed:
      logger.exception(f"推送 {data['uname']} 的直播间到目标 {target} 失败")

  coros: List[Awaitable[None]] = []
  for target in targets:
    coros.append(send_with_except(target, message))

  await asyncio.gather(*coros)


async def check() -> bool:
  total_t = time.perf_counter()

  prepare_t = time.perf_counter()
  try:
    bot = cast(Bot, nonebot.get_bot())
  except ValueError:
    return False
  params: List[str] = []
  targets: Dict[int, List[Union[GroupTarget, UserTarget]]] = {}
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
  coros: List[Awaitable[None]] = []
  for uid, detail in data["data"].items():
    current = detail["live_status"] == 1
    status = "已开播" if current else "未开播"
    logger.debug(f"B站直播: {detail['uname']} -> {status}")
    if not streaming[uid] and current:
      coros.append(push_all(bot, detail, targets[int(uid)]))
    streaming[uid] = current
  await asyncio.gather(*coros)
  send_t = time.perf_counter() - send_t

  total_t = time.perf_counter() - total_t
  if total_t > 10:
    logger.warning(
      f"检查直播时间过长，请检查网络: \n"
      f"准备 {prepare_t:.3f}s\n获取 {fetch_t:.3f}s\n发送 {send_t:.3f}s"
    )
  return bool(coros)
