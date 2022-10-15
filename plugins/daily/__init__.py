import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Awaitable, Literal, cast

import nonebot
from apscheduler.job import Job
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed
from pydantic import BaseModel, Field

from util import command, config_v2, context, util

from .modules import Module
from .modules.countdown import Countdown, CountdownModule
from .modules.furbot import FurbotModule
from .modules.history import HistoryModule
from .modules.moyu import MoyuModule, moyu_cache
from .modules.news import NewsModule, news_cache
from .modules.rank import RankModule
from .modules.sentence import SentenceModule, sentence_cache
from .modules.string import StringModule

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

_time = time


class BaseModuleConfig(BaseModel):
  type: str

  def create_module(self, group_id: int) -> Module:
    raise NotImplementedError


class StringModuleConfig(BaseModuleConfig):
  type: Literal["string"]
  string: str = "七点几勒，起床先啦！各位兽受们早上好"

  def create_module(self, group_id: int) -> Module:
    return StringModule(self.string)


class CountdownModuleConfig(BaseModuleConfig):
  type: Literal["countdown"]
  countdowns: list[Countdown]

  def create_module(self, group_id: int) -> Module:
    return CountdownModule(self.countdowns)


class NewsModuleConfig(BaseModuleConfig):
  type: Literal["news"]

  def create_module(self, group_id: int) -> Module:
    return NewsModule()


class MoyuModuleConfig(BaseModuleConfig):
  type: Literal["moyu"]

  def create_module(self, group_id: int) -> Module:
    return MoyuModule()


class HistoryModuleConfig(BaseModuleConfig):
  type: Literal["history"]

  def create_module(self, group_id: int) -> Module:
    return HistoryModule()


class SentenceModuleConfig(BaseModuleConfig):
  type: Literal["sentence"]

  def create_module(self, group_id: int) -> Module:
    return SentenceModule()


class RankModuleConfig(BaseModuleConfig):
  type: Literal["rank"]
  limit: int = 10

  def create_module(self, group_id: int) -> Module:
    return RankModule(group_id, self.limit)


class FurbotModuleConfig(BaseModuleConfig):
  type: Literal["furbot"]

  def create_module(self, group_id: int) -> Module:
    return FurbotModule()


AnyModuleConfig = \
  StringModuleConfig | \
  CountdownModuleConfig | \
  NewsModuleConfig | \
  MoyuModuleConfig | \
  HistoryModuleConfig | \
  SentenceModuleConfig | \
  RankModuleConfig | \
  FurbotModuleConfig


class GroupConfig(BaseModel):
  time: _time | None = None
  modules: list[AnyModuleConfig | list[AnyModuleConfig]] | None = None


class Config(BaseModel):
  default_time: _time = _time(7, 0, 0)
  default_modules: list[AnyModuleConfig | list[AnyModuleConfig]] = \
    Field(default_factory=list)
  groups: dict[int, GroupConfig] = Field(default_factory=dict)


class State(BaseModel):
  last_send: dict[int, date] = Field(default_factory=dict)


CONFIG = config_v2.SharedConfig("daily", Config, "eager")
STATE = config_v2.SharedState("daily", State)
driver = nonebot.get_driver()
jobs: list[Job] = []


@CONFIG.onload()
def onload(prev: Config | None, curr: Config):
  for job in jobs:
    job.remove()
  jobs.clear()
  for group, group_config in curr.groups.items():
    time = group_config.time or curr.default_time
    job = scheduler.add_job(
      check_daily, "cron", (group,), hour=time.hour, minute=time.minute, second=time.second
    )
    jobs.append(job)
    if datetime.now().time() > time:
      asyncio.create_task(check_daily(group))


@dataclass
class Forward:
  nodes: list[MessageSegment]


@driver.on_bot_connect
async def on_bot_connect() -> None:
  CONFIG.load()


async def format_one(group_id: int, module_config: BaseModuleConfig) -> util.AnyMessage:
  try:
    return await module_config.create_module(group_id).format()
  except Exception:
    logger.exception(f"每日推送模块运行失败: {module_config}")
    return f"模块运行失败：{module_config.type}"


async def format_forward(
  bot_id: int, bot_name: str, group_id: int, modules: list[AnyModuleConfig]
) -> Forward:
  coros = [format_one(group_id, module) for module in modules]
  messages = await asyncio.gather(*coros)
  return Forward([util.forward_node(bot_id, bot_name, message) for message in messages])


async def format_all(group_id: int) -> list[util.AnyMessage | Forward]:
  config = CONFIG()
  if group_id not in config.groups:
    modules = config.default_modules
  else:
    modules = config.groups[group_id].modules or config.default_modules
  bot = cast(Bot, nonebot.get_bot())
  bot_id = int(bot.self_id)
  if group_id == -1:
    info = await bot.get_login_info()
    bot_name = info["nickname"]
  else:
    info = await bot.get_group_member_info(group_id=group_id, user_id=bot_id)
    bot_name = info["card"] or info["nickname"]
  coros: list[Awaitable[util.AnyMessage | Forward]] = []
  for module in modules:
    if isinstance(module, list):
      coros.append(format_forward(bot_id, bot_name, group_id, module))
    else:
      coros.append(format_one(group_id, module))
  return await asyncio.gather(*coros)


async def try_send(bot: Bot, group_id: int, message: util.AnyMessage | Forward) -> None:
  if isinstance(message, MessageSegment):
    message = Message(message)
  try:
    if isinstance(message, Forward):
      await bot.call_api("send_group_forward_msg", group_id=group_id, messages=message.nodes)
    else:
      await bot.send_group_msg(group_id=group_id, message=message)
  except ActionFailed:
    logger.exception(f"发送部分每日推送到群聊 {group_id} 失败: {message}")
    try:
      await bot.send_group_msg(
        group_id=group_id, message="发送部分每日推送失败，可运行 /今天 重新查看"
      )
    except ActionFailed:
      pass


async def check_daily(group_id: int) -> None:
  state = STATE()
  today = date.today()
  if today <= state.last_send.get(group_id, date.min):
    return
  logger.info(f"向 {group_id} 发送每日推送")
  bot = cast(Bot, nonebot.get_bot())
  for message in await format_all(group_id):
    await try_send(bot, group_id, message)
  state.last_send[group_id] = today
  STATE.dump()


today = (
  command.CommandBuilder("daily.today", "今天")
  .brief("今天的问好你看了吗")
  .usage("包含 /摸鱼、/60s 和 /一句 的内容")
  .build())


@today.handle()
async def handle_today(bot: Bot, event: MessageEvent) -> None:
  messages = await format_all(context.get_event_context(event))
  for message in messages:
    if isinstance(message, Forward):
      await util.send_forward_msg(bot, event, *message.nodes)
    else:
      await today.send(message)


moyu = (
  command.CommandBuilder("daily.moyu", "摸鱼日历", "摸鱼")
  .brief("今天也要开心摸鱼哦")
  .usage("接口来自https://api.j4u.ink")
  .build())


@moyu.handle()
async def handle_moyu() -> None:
  await moyu_cache.ensure()
  await today.finish(util.local_image(moyu_cache.path))


news = (
  command.CommandBuilder("daily.news", "60秒", "60s")
  .brief("用60秒迅速看世界")
  .usage("接口来自https://api.qqsuu.cn")
  .build())


@news.handle()
async def handle_news() -> None:
  await news_cache.ensure()
  await today.finish(util.local_image(news_cache.path))


sentence = (
  command.CommandBuilder("daily.sentence", "每日一句", "一句")
  .brief("是中英双语的")
  .usage("接口来自http://open.iciba.com")
  .build())


@sentence.handle()
async def handle_sentence() -> None:
  await sentence_cache.ensure()
  await today.send(util.local_image(sentence_cache.path))
  await today.finish(util.local_record(sentence_cache.audio_path))


history = (
  command.CommandBuilder("daily.history", "历史")
  .brief("看看历史上的今天")
  .usage("接口来自https://www.ipip5.com/today/")
  .build())


@history.handle()
async def handle_history() -> None:
  await history.send(await HistoryModule().format())
