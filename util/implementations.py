import asyncio
from dataclasses import dataclass
from datetime import datetime
from weakref import WeakKeyDictionary

import nonebot
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment

__all__ = [
  "LAGRANGE",
  "LLONEBOT",
  "NAPCAT",
  "Rkey",
  "get_implementation",
  "get_rkey",
  "get_rkey_cached",
  "remove_reaction",
  "send_friend_poke",
  "send_group_poke",
  "send_poke",
  "send_reaction",
]


@dataclass
class Rkey:
  rkey: str
  created_at: datetime
  expire_at: datetime


driver = nonebot.get_driver()
implementations = WeakKeyDictionary[Bot, str]()
impl_locks = WeakKeyDictionary[Bot, asyncio.Lock]()
rkey_cache = WeakKeyDictionary[Bot, dict[str, Rkey]]()
rkey_locks = WeakKeyDictionary[Bot, asyncio.Lock]()
LAGRANGE = "Lagrange.OneBot"
LLONEBOT = "LLOneBot"
NAPCAT = "NapCat.Onebot"


async def get_implementation(bot: Bot) -> str:
  if bot not in implementations:
    lock = impl_locks.setdefault(bot, asyncio.Lock())
    async with lock:
      if bot not in implementations:
        info = await bot.get_version_info()
        implementations[bot] = info["app_name"]
  return implementations[bot]


@driver.on_bot_disconnect
async def on_bot_disconnect(bot: Bot) -> None:
  implementations.pop(bot, None)
  rkey_cache.pop(bot, None)


async def send_group_poke(bot: Bot, group_id: int, user_id: int) -> None:
  if await get_implementation(bot) in (LAGRANGE, NAPCAT, LLONEBOT):
    await bot.group_poke(group_id=group_id, user_id=user_id)
  else:
    message = Message(MessageSegment("poke", {"qq": user_id}))
    await bot.send_group_msg(group_id=group_id, message=message)


async def send_friend_poke(bot: Bot, user_id: int) -> None:
  if await get_implementation(bot) in (LAGRANGE, NAPCAT, LLONEBOT):
    await bot.friend_poke(user_id=user_id)
  else:
    message = Message(MessageSegment("poke", {"qq": user_id}))
    await bot.send_private_msg(user_id=user_id, message=message)


async def send_poke(bot: Bot, event: Event) -> None:
  user_id = getattr(event, "user_id", None)
  if user_id is None:
    raise ValueError("事件无用户 ID")
  group_id = getattr(event, "group_id", None)
  if group_id is None:
    await send_friend_poke(bot, user_id)
  else:
    await send_group_poke(bot, group_id, user_id)


async def send_reaction(bot: Bot, group_id: int, message_id: int, emoji_id: int) -> None:
  impl = await get_implementation(bot)
  if impl == LAGRANGE:
    await bot.set_group_reaction(
      group_id=group_id,
      message_id=message_id,
      code=emoji_id,
      is_add=True,
    )
  elif impl == LLONEBOT:
    await bot.set_msg_emoji_like(message_id=message_id, emoji_id=emoji_id)
  elif impl == NAPCAT:
    await bot.set_msg_emoji_like(message_id=message_id, emoji_id=emoji_id, set=True)
  else:
    logger.warning(f"未知 OneBot 实现 {impl!r}，无法发送表情回应")


async def remove_reaction(bot: Bot, group_id: int, message_id: int, emoji_id: int) -> None:
  impl = await get_implementation(bot)
  if impl == LAGRANGE:
    await bot.set_group_reaction(
      group_id=group_id,
      message_id=message_id,
      code=emoji_id,
      is_add=False,
    )
  elif impl == LLONEBOT:
    await bot.unset_msg_emoji_like(message_id=message_id, emoji_id=emoji_id)
  elif impl == NAPCAT:
    await bot.set_msg_emoji_like(message_id=message_id, emoji_id=emoji_id, set=False)
  else:
    logger.warning(f"未知 OneBot 实现 {impl!r}，无法发送表情回应")


async def get_rkey(bot: Bot) -> dict[str, Rkey]:
  impl = await get_implementation(bot)
  if impl == LAGRANGE:
    rkey_dicts = {
      rkey["type"]: Rkey(
        rkey["rkey"].removeprefix("&rkey="),
        datetime.fromtimestamp(rkey["created_at"]),
        datetime.fromtimestamp(rkey["created_at"] + rkey["ttl"]),
      )
      for rkey in (await bot.get_rkey())["rkeys"]
    }
  elif impl == LLONEBOT:
    rkeys = await bot.get_rkey()
    created_at = datetime.fromisoformat(rkeys["updated_time"])
    expire_at = datetime.fromtimestamp(rkeys["expired_time"])
    rkey_dicts = {
      "private": Rkey(rkeys["private_key"].removeprefix("&rkey="), created_at, expire_at),
      "group": Rkey(rkeys["group_key"].removeprefix("&rkey="), created_at, expire_at),
    }
  elif impl == NAPCAT:
    rkey_dicts = {
      rkey["type"]: Rkey(
        rkey["rkey"].removeprefix("&rkey="),
        datetime.fromtimestamp(rkey["created_at"]),
        datetime.fromtimestamp(rkey["created_at"] + int(rkey["ttl"])),
      )
      for rkey in await bot.get_rkey()
    }
  else:
    raise ValueError(f"未知 OneBot 实现 {impl!r}，无法获取 rkey")
  rkey_cache[bot] = rkey_dicts
  return rkey_dicts


def _is_rkey_cache_valid(bot: Bot) -> bool:
  if bot not in rkey_cache:
    return False
  now = datetime.now()
  return all(now < rkey.expire_at for rkey in rkey_cache[bot].values())


async def get_rkey_cached(bot: Bot) -> dict[str, Rkey]:
  if not _is_rkey_cache_valid(bot):
    lock = rkey_locks.setdefault(bot, asyncio.Lock())
    async with lock:
      if not _is_rkey_cache_valid(bot):
        return await get_rkey(bot)
  return rkey_cache[bot]
