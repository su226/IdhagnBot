import nonebot
from nonebot.adapters.onebot.v11 import Bot, PokeNotifyEvent

from util import context, implementations, permission


async def is_poke(event: PokeNotifyEvent) -> bool:
  return event.user_id != event.self_id and event.target_id == event.self_id
auto_repoke = nonebot.on(
  "notice",
  is_poke,
  context.build_permission(("auto_repoke",), permission.Level.MEMBER),
)
@auto_repoke.handle()
async def handle_auto_repoke(bot: Bot, event: PokeNotifyEvent):
  await implementations.send_poke(bot, event)
