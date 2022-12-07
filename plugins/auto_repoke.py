import nonebot
from nonebot.adapters.onebot.v11 import MessageSegment, PokeNotifyEvent

from util import context, permission


async def is_poke(event: PokeNotifyEvent) -> bool:
  return event.user_id != event.self_id and event.target_id == event.self_id
auto_repoke = nonebot.on(
  "notice",
  is_poke,
  context.build_permission(("auto_repoke",), permission.Level.MEMBER),
)
@auto_repoke.handle()
async def handle_auto_repoke(event: PokeNotifyEvent):
  await auto_repoke.finish(MessageSegment("poke", {"qq": event.user_id}))
