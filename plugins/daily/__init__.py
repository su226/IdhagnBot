import asyncio
import itertools
from dataclasses import dataclass
from datetime import date, datetime, time as time_, timedelta
from typing import Awaitable, Dict, List, Literal, Optional, Union, cast

import nonebot
from apscheduler.job import Job
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed
from pydantic import BaseModel, Field

from util import command, configs, context, misc

from .modules import Module
from .modules.countdown import Countdown, CountdownModule
from .modules.epicgames import EpicGamesModule
from .modules.epicgames_android import EpicGamesAndroidModule
from .modules.furbot import FurbotModule
from .modules.history import HistoryModule
from .modules.moyu import MoyuModule, moyu_cache
from .modules.news import NewsModule, news_cache
from .modules.rank import RankModule
from .modules.sentence import SentenceModule, sentence_cache
from .modules.string import StringModule
from .modules.unrealassets import UnrealAssetsModule

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402


class BaseModuleConfig(BaseModel):
  # 整个类都 frozen 时能正确推断，但单字段 frozen 不能正确推断，只能忽略报错
  type: str = Field(frozen=True)

  def create_module(self, group_id: int) -> Module:
    raise NotImplementedError


class StringModuleConfig(BaseModuleConfig):
  type: Literal["string"] = Field(frozen=True)  # type: ignore
  string: str = "七点几勒，起床先啦！各位兽受们早上好"

  def create_module(self, group_id: int) -> Module:
    return StringModule(self.string)


class CountdownModuleConfig(BaseModuleConfig):
  type: Literal["countdown"] = Field(frozen=True)  # type: ignore
  countdowns: List[Countdown]

  def create_module(self, group_id: int) -> Module:
    return CountdownModule(self.countdowns)


class NewsModuleConfig(BaseModuleConfig):
  type: Literal["news"] = Field(frozen=True)  # type: ignore

  def create_module(self, group_id: int) -> Module:
    return NewsModule()


class MoyuModuleConfig(BaseModuleConfig):
  type: Literal["moyu"] = Field(frozen=True)  # type: ignore

  def create_module(self, group_id: int) -> Module:
    return MoyuModule()


class HistoryModuleConfig(BaseModuleConfig):
  type: Literal["history"] = Field(frozen=True)  # type: ignore

  def create_module(self, group_id: int) -> Module:
    return HistoryModule()


class SentenceModuleConfig(BaseModuleConfig):
  type: Literal["sentence"] = Field(frozen=True)  # type: ignore

  def create_module(self, group_id: int) -> Module:
    return SentenceModule()


class RankModuleConfig(BaseModuleConfig):
  type: Literal["rank"] = Field(frozen=True)  # type: ignore
  limit: int = 10

  def create_module(self, group_id: int) -> Module:
    return RankModule(group_id, self.limit)


class FurbotModuleConfig(BaseModuleConfig):
  type: Literal["furbot"] = Field(frozen=True)  # type: ignore

  def create_module(self, group_id: int) -> Module:
    return FurbotModule()


class EpicGamesModuleConfig(BaseModuleConfig):
  type: Literal["epicgames"] = Field(frozen=True)  # type: ignore
  force: bool = False

  def create_module(self, group_id: int) -> Module:
    return EpicGamesModule(self.force)


class EpicGamesAndroidModuleConfig(BaseModuleConfig):
  type: Literal["epicgames_android"] = Field(frozen=True)  # type: ignore
  force: bool = False

  def create_module(self, group_id: int) -> Module:
    return EpicGamesAndroidModule(self.force)


class UnrealAssetsModuleConfig(BaseModuleConfig):
  type: Literal["unrealassets"] = Field(frozen=True)  # type: ignore
  force: bool = False

  def create_module(self, group_id: int) -> Module:
    return UnrealAssetsModule(self.force)


AnyModuleConfig = Union[
  StringModuleConfig,
  CountdownModuleConfig,
  NewsModuleConfig,
  MoyuModuleConfig,
  HistoryModuleConfig,
  SentenceModuleConfig,
  RankModuleConfig,
  FurbotModuleConfig,
  EpicGamesModuleConfig,
  EpicGamesAndroidModuleConfig,
  UnrealAssetsModuleConfig,
]
ModuleOrForward = Union[AnyModuleConfig, List[AnyModuleConfig]]


class GroupConfig(BaseModel):
  time: Optional[time_] = None
  modules: Optional[List[ModuleOrForward]] = None


class Config(BaseModel):
  default_time: time_ = time_(7, 0, 0)
  default_modules: List[ModuleOrForward] = Field(default_factory=list)
  grace_time: timedelta = timedelta(minutes=10)
  groups: Dict[int, GroupConfig] = Field(default_factory=dict)


class State(BaseModel):
  # 应该重命名为 last_check
  last_send: Dict[int, date] = Field(default_factory=dict)


CONFIG = configs.SharedConfig("daily", Config, "eager")
STATE = configs.SharedState("daily", State)
driver = nonebot.get_driver()
jobs: List[Job] = []


@CONFIG.onload()
def onload(prev: Optional[Config], curr: Config):
  for job in jobs:
    job.remove()
  jobs.clear()
  now = datetime.now().time()
  grace_time = int(curr.grace_time.total_seconds())
  for group, group_config in curr.groups.items():
    if group == -1:
      continue
    send_time = group_config.time or curr.default_time
    jobs.append(scheduler.add_job(
      check_daily,
      "cron",
      (group,),
      hour=send_time.hour,
      minute=send_time.minute,
      second=send_time.second,
      misfire_grace_time=grace_time,
      coalesce=True,
    ))
    if now > send_time:
      asyncio.create_task(check_daily(group))


@dataclass
class Forward:
  nodes: List[MessageSegment]


@driver.on_bot_connect
async def on_bot_connect() -> None:
  CONFIG()


async def format_one(group_id: int, module_config: BaseModuleConfig) -> List[Message]:
  try:
    return await module_config.create_module(group_id).format()
  except Exception:
    logger.exception(f"每日推送模块运行失败: {module_config}")
    return [Message(MessageSegment.text(f"模块运行失败：{module_config.type}"))]


async def format_forward(
  bot_id: int, bot_name: str, group_id: int, modules: List[AnyModuleConfig],
) -> Forward:
  coros = [format_one(group_id, module) for module in modules]
  messages = await asyncio.gather(*coros)
  return Forward([
    misc.forward_node(bot_id, bot_name, message)
    for message in itertools.chain.from_iterable(messages)
  ])


async def format_all(group_id: int) -> List[Union[Message, Forward]]:
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
  coros: List[Awaitable[Union[List[Message], Forward]]] = []
  for module in modules:
    if isinstance(module, list):
      coros.append(format_forward(bot_id, bot_name, group_id, module))
    else:
      coros.append(format_one(group_id, module))
  result: List[Union[Message, Forward]] = []
  for i in await asyncio.gather(*coros):
    if isinstance(i, Forward):
      result.append(i)
    else:
      result.extend(i)
  return result


def clean_message(message: Union[Message, Forward]) -> None:
  # 清除消息中的 base64，防止日志过长
  if isinstance(message, Forward):
    for node in message.nodes:
      clean_message(node.data["content"])
    return
  for seg in message:
    if "file" in seg.data and seg.data["file"].startswith("base64://"):
      seg.data["file"] = "base64://..."


async def check_daily(group_id: int) -> None:
  state = STATE()
  now = datetime.now()
  today = now.date()
  if today <= state.last_send.get(group_id, date.min):
    return
  config = CONFIG()
  today_end = datetime.combine(today, time_(23, 59, 59, 999999))
  send_datetime = datetime.combine(today, config.groups[group_id].time or config.default_time)
  send_datetime_max = min(send_datetime + config.grace_time, today_end)
  if now > send_datetime_max:
    logger.warning(f"超过最大发送时间，将不会向 {group_id} 发送每日推送")
  else:
    logger.info(f"向 {group_id} 发送每日推送")
    await send_daily(group_id)
  state.last_send[group_id] = today
  STATE.dump()


async def send_daily(group_id: int) -> None:
  bot = cast(Bot, nonebot.get_bot())
  failed = False
  for message in await format_all(group_id):
    try:
      if isinstance(message, Forward):
        await bot.send_group_forward_msg(group_id=group_id, messages=message.nodes)
      else:
        await bot.send_group_msg(group_id=group_id, message=message)
    except ActionFailed:
      clean_message(message)
      logger.exception(f"发送部分每日推送到群聊 {group_id} 失败: {message}")
      failed = True
  if failed:
    try:
      await bot.send_group_msg(
        group_id=group_id, message="发送部分每日推送失败，可运行 /今天 重新查看",
      )
    except ActionFailed:
      pass


today = (
  command.CommandBuilder("daily.today", "今天")
  .brief("今天的问好你看了吗")
  .usage("通常包含 /摸鱼、/60s 和 /一句 的内容")
  .build()
)
@today.handle()
async def handle_today(bot: Bot, event: MessageEvent) -> None:
  messages = await format_all(context.get_event_context(event))
  for message in messages:
    if isinstance(message, Forward):
      await misc.send_forward_msg(bot, event, *message.nodes)
    else:
      await today.send(message)


moyu = (
  command.CommandBuilder("daily.moyu", "摸鱼日历", "摸鱼")
  .brief("今天也要开心摸鱼哦")
  .usage("接口来自https://api.j4u.ink")
  .build()
)
@moyu.handle()
async def handle_moyu() -> None:
  await moyu_cache.ensure()
  await today.finish(misc.local("image", moyu_cache.path))


news = (
  command.CommandBuilder("daily.news", "60秒", "60s")
  .brief("用60秒迅速看世界")
  .usage("接口来自https://api.tangdouz.com")
  .build()
)
@news.handle()
async def handle_news() -> None:
  await news_cache.ensure()
  await today.finish(misc.local("image", news_cache.path))


sentence = (
  command.CommandBuilder("daily.sentence", "每日一句", "一句")
  .brief("是中英双语的")
  .usage("接口来自http://open.iciba.com")
  .build()
)
@sentence.handle()
async def handle_sentence() -> None:
  await sentence_cache.ensure()
  await sentence.send(misc.local("image", sentence_cache.path))
  await sentence.finish(misc.local("record", sentence_cache.audio_path))


history = (
  command.CommandBuilder("daily.history", "历史")
  .brief("看看历史上的今天")
  .usage("接口来自https://baike.baidu.com/calendar/")
  .build()
)
@history.handle()
async def handle_history() -> None:
  await history.finish(await HistoryModule().raw_format())
