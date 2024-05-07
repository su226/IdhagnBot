import json
import re
from datetime import timedelta
from typing import Any, Dict, List, Optional, Sequence, cast

import emoji
import nonebot
import wordcloud
from jieba.analyse.tfidf import TFIDF
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.typing import T_State
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from util import configs, context, imutil, misc, record
from util.command import CommandBuilder
from util.dateutil import DATE_ARGS_USAGE, parse_date_range_args


class Config(BaseModel):
  font: Optional[str] = None
  width: int = 400
  height: int = 200
  scale: float = 1
  bg: int = 0xffffff
  # https://matplotlib.org/stable/tutorials/colors/colormaps.html
  fg: str = "viridis"
  limit: int = 0
  idf_path: str = ""
  stopwords_path: str = ""

CONFIG = configs.SharedConfig("wordcloud", Config)

# https://github.com/he0119/nonebot-plugin-wordcloud/blob/main/nonebot_plugin_wordcloud/data_source.py#L18
# 这个又是从 https://stackoverflow.com/a/17773849/9212748 搬的
# 二道贩子（雾）
URL_RE = re.compile(r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})")  # noqa: E501

driver = nonebot.get_driver()

def format_wordcloud(messages: Sequence[str]) -> MessageSegment:
  config = CONFIG()
  texts: List[str] = []
  for i in messages:
    data: List[Dict[str, Any]] = json.loads(i)
    plain = " ".join([x["data"]["text"] for x in data if x["type"] == "text"]).strip()
    is_command = False
    for start in driver.config.command_start:
      if start and plain.startswith(start):
        is_command = True
        break
    if is_command:
      continue
    plain = URL_RE.sub("", plain)
    plain = emoji.replace_emoji(plain)
    texts.append(plain)
  tfidf = TFIDF(config.idf_path)
  if config.stopwords_path:
    tfidf.set_stop_words(config.stopwords_path)
  tags = cast(Dict[str, float], tfidf.extract_tags("\n".join(texts), 0, True))
  wc = wordcloud.WordCloud(
    config.font,
    config.width,
    config.height,
    background_color=cast(str, config.bg),
    colormap=config.fg,
  )
  im = wc.generate_from_frequencies(tags).to_image()
  return imutil.to_segment(im)


group_wordcloud = (
  CommandBuilder("wordcloud.group", "群词云", "词云")
  .brief("查看最近的群词云")
  .usage(DATE_ARGS_USAGE)
  .in_group()
  .state(is_user=False)
  .build()
)
personal_wordcloud = (
  CommandBuilder("wordcloud.personal", "个人词云", "我的词云")
  .brief("查看最近的个人词云")
  .usage(DATE_ARGS_USAGE)
  .state(is_user=True)
  .build()
)
@group_wordcloud.handle()
@personal_wordcloud.handle()
async def handle_wordcloud(
  bot: Bot, event: MessageEvent, state: T_State, arg: Message = CommandArg(),
) -> None:
  start_datetime, end_datetime = await parse_date_range_args(arg)
  config = CONFIG()
  group_id = context.get_event_context(event)
  user_id = event.user_id
  is_user = state["is_user"]

  async with AsyncSession(record.engine) as session:
    query = select(record.Received.content)
    if group_id != -1:
      query = query.where(record.Received.group_id == group_id)
    if is_user:
      query = query.where(record.Received.user_id == user_id)
    result = await session.execute(
      query.where(
        record.Received.time >= start_datetime,
        record.Received.time < end_datetime,
      )
      .order_by(func.random())
      .limit(None if config.limit == 0 else config.limit),
    )
    messages = result.scalars().all()

  end_datetime -= timedelta(seconds=1)  # 显示 23:59:59 而不是 00:00:00，以防误会
  try:
    seg = await misc.to_thread(format_wordcloud, messages)
  except ValueError:
    await Matcher.finish((
      f"{start_datetime:%Y-%m-%d %H:%M:%S} 到 {end_datetime:%Y-%m-%d %H:%M:%S} 内没有数据"
    ))
  title = f"{start_datetime:%Y-%m-%d %H:%M:%S} 到 {end_datetime:%Y-%m-%d %H:%M:%S} 的词云"
  if is_user:
    name = await context.get_card_or_name(bot, group_id, user_id)
    title = f"{name} {title}"
  if group_id != -1:
    group_info = await bot.get_group_info(group_id=group_id)
    title = f"{group_info['group_name']} 群内 {title}"
  await Matcher.finish(title + seg)
