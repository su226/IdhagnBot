import asyncio
import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

import nonebot
from nonebot.adapters.onebot.v11 import Event, MessageEvent, MessageSegment
from nonebot.message import event_postprocessor
from pydantic.json import pydantic_encoder
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Field as SQLField, MetaData, SQLModel as BaseSQLModel, select

from util import hook


class SQLModel(BaseSQLModel):
  metadata = MetaData()


class Received(SQLModel, table=True):
  message_id: int = SQLField(primary_key=True)
  time: datetime
  user_id: int
  group_id: int | None
  content: str


class Sent(SQLModel, table=True):
  message_id: int = SQLField(primary_key=True)
  time: datetime
  is_group: bool
  target_id: int
  caused_by: int | None = SQLField(foreign_key="received.message_id")
  content: str


class Cache(SQLModel, table=True):
  md5: str = SQLField(primary_key=True)
  type: str
  created: datetime
  last_seen: datetime


@dataclass
class CacheEntry:
  type: str
  md5: str


os.makedirs("states/messages", exist_ok=True)
engine = create_async_engine("sqlite+aiosqlite:///states/messages/messages.db")
driver = nonebot.get_driver()


@driver.on_startup
async def on_startup():
  async with engine.begin() as connection:
    await connection.run_sync(SQLModel.metadata.create_all)


AnySegment = str | MessageSegment | dict
AnyMessage = Iterable[MessageSegment | dict]


def process_segment(segment: AnySegment) -> tuple[list[CacheEntry], dict]:
  if isinstance(segment, str):
    return [], {"type": "text", "data": {"text": segment}}
  elif isinstance(segment, MessageSegment):
    type = segment.type
    data = segment.data
  else:
    type = segment["type"]
    data = segment["data"]
  caches = []
  if type in ("image", "record", "video"):
    file = data.get("file", "")
    if file.startswith("base64://"):
      content = base64.b64decode(file[9:])
      md5 = hashlib.md5(content).hexdigest()
      basedir = os.path.abspath(f"states/messages/{type}")
      path = os.path.join(basedir, md5)
      if not os.path.exists(path):
        os.makedirs(basedir, exist_ok=True)
        with open(path, "wb") as f:
          f.write(content)
      data["file"] = f"file://{path}"
      caches.append(CacheEntry(type, md5))
  elif type == "node":
    caches, data["content"] = process_message(data["content"])
  return caches, {"type": type, "data": data}


def process_message(message: AnySegment | AnyMessage) -> tuple[list[CacheEntry], list]:
  if isinstance(message, AnySegment):
    caches, segment = process_segment(message)
    return caches, [segment]
  caches: list[CacheEntry] = []
  segments: list[dict] = []
  for raw in message:
    cache, segment = process_segment(raw)
    caches.extend(cache)
    segments.append(segment)
  return caches, segments


def serialize_message(message: AnySegment | AnyMessage) -> tuple[list[CacheEntry], str]:
  caches, segments = process_message(message)
  return caches, json.dumps(segments, ensure_ascii=False, default=pydantic_encoder)


async def process_caches(session: AsyncSession, caches: list[CacheEntry]) -> None:
  selections = (session.execute(select(Cache).where(Cache.md5 == cache.md5)) for cache in caches)
  for cache, result in zip(caches, await asyncio.gather(*selections)):
    row = result.one_or_none()
    now = datetime.now()
    if not row:
      item = Cache(md5=cache.md5, type=cache.type, created=now, last_seen=now)
    else:
      item, = row
      item.last_seen = now
    session.add(item)


@hook.on_message_sent
async def on_message_sent(
  event: Event | None, is_group: bool, target_id: int, message: Any, message_id: int
) -> None:
  if not message_id:
    return
  caused_by = None
  if isinstance(event, MessageEvent) and event.message_id:
    caused_by = event.message_id
  caches, segments = serialize_message(message)
  async with AsyncSession(engine) as session:
    await process_caches(session, caches)
    session.add(Sent(
      message_id=message_id,
      time=datetime.now(),
      is_group=is_group,
      target_id=target_id,
      content=segments,
      caused_by=caused_by
    ))
    await session.commit()


@event_postprocessor
async def on_message_event(event: Event) -> None:
  # 类型标注得是 Event，不然 DEBUG 日志会被 HeartbeatEvent 刷屏
  if not isinstance(event, MessageEvent) or not event.message_id:
    return
  caches, segments = serialize_message(event.message)
  async with AsyncSession(engine) as session:
    await process_caches(session, caches)
    session.add(Received(
      message_id=event.message_id,
      time=datetime.fromtimestamp(event.time),
      user_id=event.user_id,
      group_id=getattr(event, "group_id", None),
      content=segments
    ))
    await session.commit()
