from weakref import WeakKeyDictionary

import asyncio
import nonebot
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment

__all__ = [
  "get_implementation", "send_group_poke", "send_friend_poke", "send_poke", "send_reaction",
]
driver = nonebot.get_driver()
implementations = WeakKeyDictionary[Bot, str]()
impl_locks = WeakKeyDictionary[Bot, asyncio.Lock]() 


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
  try:
    del implementations[bot]
  except KeyError:
    pass


async def send_group_poke(bot: Bot, group_id: int, user_id: int) -> None:
  if await get_implementation(bot) == "Lagrange.OneBot":
    await bot.group_poke(group_id=group_id, user_id=user_id)
  else:
    message = Message(MessageSegment("poke", {"qq": user_id}))
    await bot.send_group_msg(group_id=group_id, message=message)


async def send_friend_poke(bot: Bot, user_id: int) -> None:
  if await get_implementation(bot) == "Lagrange.OneBot":
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
