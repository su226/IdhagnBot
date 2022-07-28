import asyncio
from datetime import date, datetime, time
from typing import Awaitable, cast

import nonebot
from apscheduler.job import Job
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebot.exception import ActionFailed
from pydantic import BaseModel, Field

from util import command, config_v2, resources

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


class Countdown(BaseModel):
  date: date
  before: str = ""
  exact: str = ""
  after: str = ""


class Config(BaseModel):
  _time = time
  time: _time = _time(7, 0, 0)
  groups: list[int] = Field(default_factory=list)
  countdown: list[Countdown] = Field(default_factory=list)


class State(BaseModel):
  last_send: date = date.min


CONFIG = config_v2.SharedConfig("daily", Config)
STATE = config_v2.SharedState("daily", State)
driver = nonebot.get_driver()
job: Job | None = None


@CONFIG.onload(False)
def onload(prev: Config | None, curr: Config):
  global job
  now = datetime.now()
  if job:
    job.remove()
  job = scheduler.add_job(
    send_daily, "cron", hour=curr.time.hour, minute=curr.time.minute, second=curr.time.second)
  if now.time() >= curr.time:
    asyncio.create_task(send_daily())


@driver.on_bot_connect
async def on_bot_connect() -> None:
  CONFIG.load()


SENTENCE_API = "http://open.iciba.com/dsapi/"
NEWS_API = "https://api.qqsuu.cn/api/60s"
MOYU_API = "https://api.j4u.ink/v1/store/other/proxy/remote/moyu.json"
TODAY_API = "https://www.ipip5.com/today/api.php?type=json"


async def fetch_history() -> str:
  http = resources.http()
  async with http.get(TODAY_API) as response:
    data = await response.json()
  result = []
  for i in data["result"][:-1]:
    result.append(f"{i['year']}: {i['title']}")
  return "\n".join(result)


async def fetch_sentence() -> tuple[bytes, str]:
  http = resources.http()
  async with http.get(SENTENCE_API) as response:
    data = await response.json(content_type=None)
  async with http.get(data["fenxiang_img"]) as response:
    return await response.read(), data["tts"]


async def fetch_news() -> bytes:
  http = resources.http()
  async with http.get(NEWS_API) as response:
    return await response.read()


async def fetch_moyu() -> bytes:
  http = resources.http()
  async with http.get(MOYU_API) as response:
    data = await response.json()
  async with http.get(data["data"]["moyu_url"]) as response:
    return await response.read()


async def build_daily_message() -> Message:
  (sentence, _), news, moyu = await asyncio.gather(fetch_sentence(), fetch_news(), fetch_moyu())
  config = CONFIG()
  today = date.today()
  countdowns: list[str] = []
  for i in config.countdown:
    delta = (i.date - today).days
    if delta > 0 and i.before:
      countdowns.append(i.before.format(delta))
    elif delta == 0 and i.exact:
      countdowns.append(i.exact)
    elif delta < 0 and i.after:
      countdowns.append(i.after.format(-delta))
  return (
    f"大家好，今天是{today.year}年{today.month}月{today.day}日，也是：\n"
    + "\n".join(countdowns) + "\n还可以试试发送 /历史 看看历史上的今天"
    + "\n今天的「摸鱼日历」是：\n" + MessageSegment.image(moyu)
    + "\n再用「60秒」看看世界：\n" + MessageSegment.image(news)
    + "\n最后送上「每日一句」：\n" + MessageSegment.image(sentence)
    + "\n你可以发送 /摸鱼、/60s 或者 /一句 重新查看上面的内容，也可以发送 /今天 再次看到以上全部")


async def send_daily() -> None:
  state = STATE()
  today = date.today()
  if today <= state.last_send:
    return
  config = CONFIG()
  coros: list[Awaitable[None]] = []
  try:
    message = await build_daily_message()
  except Exception:
    message = "获取每日推送失败，本消息仅做续火之用"
  bot = cast(Bot, nonebot.get_bot())

  async def send(group: int) -> None:
    try:
      await bot.send_group_msg(group_id=group, message=message)
    except ActionFailed:
      await bot.send_group_msg(group_id=group, message="发送每日推送失败，本消息仅做续火之用")

  for group in config.groups:
    coros.append(send(group))
  await asyncio.gather(*coros)
  state.last_send = today
  STATE.dump()


today = (
  command.CommandBuilder("daily.today", "今天")
  .brief("今天的问好你看了吗")
  .usage("包含 /摸鱼、/60s 和 /一句 的内容")
  .build())


@today.handle()
async def handle_today() -> None:
  await today.finish(await build_daily_message())


moyu = (
  command.CommandBuilder("daily.moyu", "摸鱼日历", "摸鱼")
  .brief("今天也要开心摸鱼哦")
  .usage("接口来自https://api.j4u.ink")
  .build())


@moyu.handle()
async def handle_moyu() -> None:
  await today.finish(MessageSegment.image(await fetch_moyu()))


news = (
  command.CommandBuilder("daily.news", "60秒", "60s")
  .brief("用60秒迅速看世界")
  .usage("接口来自https://api.qqsuu.cn")
  .build())


@news.handle()
async def handle_news() -> None:
  await today.finish(MessageSegment.image(await fetch_news()))


sentence = (
  command.CommandBuilder("daily.sentence", "每日一句", "一句")
  .brief("是中英双语的")
  .usage("接口来自http://open.iciba.com")
  .build())


@sentence.handle()
async def handle_sentence() -> None:
  image, speech = await fetch_sentence()
  await today.send(MessageSegment.image(image))
  await today.finish(MessageSegment.record(speech))


history = (
  command.CommandBuilder("daily.history", "历史")
  .brief("看看历史上的今天")
  .usage("接口来自https://www.ipip5.com/today/")
  .build())


@history.handle()
async def handle_history() -> None:
  today = date.today()
  header = f"今天是{today.year}年{today.month}月{today.day}日，历史上的今天是：\n"
  await history.finish(header + await fetch_history())
