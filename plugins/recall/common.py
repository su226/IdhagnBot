from datetime import datetime, timedelta
from io import StringIO
from typing import Dict, Iterator, MutableMapping, Optional, TypeVar

import nonebot
from apscheduler.job import Job
from apscheduler.jobstores.base import JobLookupError
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.exception import ActionFailed

from util import context, permission

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

TKey = TypeVar("TKey")
TValue = TypeVar("TValue")
class AutoDeleteDict(MutableMapping[TKey, TValue]):
  def __init__(self, ttl: float) -> None:
    self.__data: Dict[TKey, TValue] = {}
    self.__jobs: Dict[TKey, Job] = {}
    self.__ttl = ttl

  def __getitem__(self, key: TKey) -> TValue:
    return self.__data[key]

  def __setitem__(self, key: TKey, value: TValue) -> None:
    self.__data[key] = value
    date = datetime.now() + timedelta(seconds=self.__ttl)
    if key in self.__jobs:
      self.__jobs[key] = self.__jobs[key].reschedule("date", run_date=date)
    else:
      self.__jobs[key] = scheduler.add_job(self.__try_delitem, "date", (key,), run_date=date)

  def __delitem__(self, key: TKey) -> None:
    del self.__data[key]
    if key in self.__jobs:
      try:
        self.__jobs[key].remove()
      except JobLookupError:
        pass
      del self.__jobs[key]

  def __try_delitem(self, key: TKey) -> None:
    if key in self:
      del self[key]

  def __len__(self) -> int:
    return len(self.__data)

  def __iter__(self) -> Iterator[TKey]:
    return iter(self.__data)


recall_others_permission = context.build_permission(
  ("recall", "manual_recall", "others"), permission.Level.ADMIN
)


def extract_text(self_id: int, message: Message) -> Optional[str]:
  f = StringIO()
  for seg in message:
    if seg.type == "text":
      f.write(seg.data["text"])
    elif seg.type == "at":
      if seg.data["qq"] != str(self_id):
        return None
    else:
      return None
  return f.getvalue()


def has_keyword(event: MessageEvent, *keywords: str) -> bool:
  if event.reply is None or event.reply.sender.user_id != event.self_id:
    return False

  text = extract_text(event.self_id, event.message)
  return bool(text) and text.strip() in keywords


async def try_delete_msg(bot: Bot, id: int):
  try:
    await bot.delete_msg(message_id=id)
  except ActionFailed:
    pass


def schedule_delete(bot: Bot, message_id: int, delay: float) -> Job:
  return scheduler.add_job(
    try_delete_msg, "date", (bot, message_id), run_date=datetime.now() + timedelta(seconds=30)
  )
