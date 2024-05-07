import asyncio
import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypeVar, cast

import nonebot
from nonebot.adapters.onebot.v11 import (
  Event, FriendRecallNoticeEvent, GroupRecallNoticeEvent, Message, MessageEvent, MessageSegment,
)
from nonebot.message import event_preprocessor
from pydantic.json import pydantic_encoder
from sqlalchemy.engine import Connection, Inspector
from sqlalchemy.engine.interfaces import ReflectedColumn
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.ddl import DDL
from sqlmodel import Field as SQLField, MetaData, SQLModel as BaseSQLModel, inspect, select, col

from util import hook


class SQLModel(BaseSQLModel):
  metadata = MetaData()


class Received(SQLModel, table=True):
  id: Optional[int] = SQLField(primary_key=True, default=None)
  message_id: int  # 我是做梦也没想到 go-cqhttp 的消息 ID 居然会重复（）
  time: datetime
  user_id: int
  group_id: Optional[int]
  content: str
  deleted_by: Optional[int] = None


class Sent(SQLModel, table=True):
  id: Optional[int] = SQLField(primary_key=True, default=None)
  message_id: int
  time: datetime
  is_group: bool
  target_id: int
  caused_by: Optional[int] = SQLField(foreign_key="received.message_id")
  content: str
  deleted_by: Optional[int] = None


class Cache(SQLModel, table=True):
  md5: str = SQLField(primary_key=True)
  type: str
  created: datetime
  last_seen: datetime


class Version(SQLModel, table=True):
  version: int = SQLField(primary_key=True)


@dataclass
class CacheEntry:
  type: str
  md5: str


os.makedirs("states/messages", exist_ok=True)
engine = create_async_engine("sqlite+aiosqlite:///states/messages/messages.db")
driver = nonebot.get_driver()
T = TypeVar("T")
CURRENT_VERSION = 1


def _get_columns(inspector: Inspector, table: str) -> Dict[str, ReflectedColumn]:
  return {column["name"]: column for column in inspector.get_columns(table)}


def _append_column(connection: Connection, column: InstrumentedAttribute[Any]) -> None:
  connection.execute(DDL("ALTER TABLE %(table)s ADD %(column)s %(type)s", {
    "table": column.table, "column": column.key, "type": column.type,
  }))


def _col(col: T) -> InstrumentedAttribute[T]:
  if isinstance(col, InstrumentedAttribute):
    return col
  raise TypeError


def _upgrade_0to1(connection: Connection) -> None:
  # 版本 0：无 Version 表，Received 和 Sent 表无 deleted_by 列
  inspector = inspect(connection)
  tables = set(inspector.get_table_names())
  if cast(str, Version.__tablename__) in tables:
    return
  if (received := cast(str, Received.__tablename__)) in tables:
    columns = _get_columns(inspector, received)
    if (deleted_by := _col(Received.deleted_by)).key not in columns:
      _append_column(connection, deleted_by)
  if (sent := cast(str, Sent.__tablename__)) in tables:
    columns = _get_columns(inspector, sent)
    if (deleted_by := _col(Sent.deleted_by)).key not in columns:
      _append_column(connection, deleted_by)


@driver.on_startup
async def on_startup():
  async with engine.begin() as connection:
    await connection.run_sync(_upgrade_0to1)
    await connection.run_sync(Received.metadata.create_all)
    async with AsyncSession(connection) as session:
      result = (await session.execute(select(Version))).scalars().all()
      if result:
        result[0].version = CURRENT_VERSION
        session.add(result[0])
        for i in result[1:]:
          await session.delete(i)
      else:
        session.add(Version(version=CURRENT_VERSION))
      await session.commit()


def process_segment(segment: MessageSegment) -> List[CacheEntry]:
  caches: List[CacheEntry] = []
  if segment.type in ("image", "record", "video"):
    file = segment.data.get("file", "")
    if file.startswith("base64://"):
      content = base64.b64decode(file[9:])
      md5 = hashlib.md5(content).hexdigest()
      basedir = os.path.abspath(f"states/messages/{segment.type}")
      path = os.path.join(basedir, md5)
      if not os.path.exists(path):
        os.makedirs(basedir, exist_ok=True)
        with open(path, "wb") as f:
          f.write(content)
      segment.data["file"] = f"file://{path}"
      caches.append(CacheEntry(segment.type, md5))
  elif segment.type == "node":
    forward_caches, message = process_message(segment.data["content"])
    caches.extend(forward_caches)
    segment.data["content"] = message
  return caches


def process_message(message: Message) -> Tuple[List[CacheEntry], List[MessageSegment]]:
  caches: List[CacheEntry] = []
  for segment in message:
    caches.extend(process_segment(segment))
  return caches, list(message)


def serialize_message(message: Message) -> Tuple[List[CacheEntry], str]:
  caches, segments = process_message(message)
  return caches, json.dumps(segments, ensure_ascii=False, default=pydantic_encoder)


async def process_caches(session: AsyncSession, caches: List[CacheEntry]) -> None:
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
  event: Optional[Event], is_group: bool, target_id: int, message: Message, message_id: int,
) -> None:
  if not message_id:
    return
  caused_by = None
  if isinstance(event, MessageEvent) and event.message_id:
    caused_by = event.message_id
  caches, segments = serialize_message(message.copy())
  async with AsyncSession(engine) as session:
    await process_caches(session, caches)
    session.add(Sent(
      message_id=message_id,
      time=datetime.now(),
      is_group=is_group,
      target_id=target_id,
      content=segments,
      caused_by=caused_by,
    ))
    await session.commit()


@event_preprocessor
async def on_message_event(event: Event) -> None:
  # 类型标注得是 Event，不然 DEBUG 日志会被 HeartbeatEvent 刷屏
  if isinstance(event, GroupRecallNoticeEvent):
    async with AsyncSession(engine) as session:
      if event.user_id == event.self_id:
        result = await session.execute(select(Sent).where(
          Sent.message_id == event.message_id,
          col(Sent.is_group).is_(True),
          Sent.target_id == event.group_id,
        ))
      else:
        result = await session.execute(select(Received).where(
          Received.message_id == event.message_id,
          Received.user_id == event.user_id,
          Received.group_id == event.group_id,
        ))
      for record in result.scalars().all():
        record.deleted_by = event.operator_id
        session.add(record)
      await session.commit()
  elif isinstance(event, FriendRecallNoticeEvent):
    async with AsyncSession(engine) as session:
      result = await session.execute(select(Received).where(
        Received.message_id == event.message_id,
        Received.user_id == event.user_id,
        col(Received.group_id).is_(None),
      ))
      for record in result.scalars().all():
        record.deleted_by = event.user_id
        session.add(record)
      result = await session.execute(select(Sent).where(
        Sent.message_id == event.message_id,
        col(Sent.is_group).is_(False),
        Sent.target_id == event.user_id,
      ))
      for record in result.scalars().all():
        record.deleted_by = event.self_id
        session.add(record)
      await session.commit()
  elif isinstance(event, MessageEvent):
    if not event.message_id:
      return
    caches, segments = serialize_message(event.message)
    async with AsyncSession(engine) as session:
      await process_caches(session, caches)
      session.add(Received(
        message_id=event.message_id,
        time=datetime.fromtimestamp(event.time),
        user_id=event.user_id,
        group_id=getattr(event, "group_id", None),
        content=segments,
      ))
      await session.commit()
