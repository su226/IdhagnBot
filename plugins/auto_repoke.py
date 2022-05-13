from nonebot.adapters.onebot.v11 import Event, MessageSegment
from nonebot.rule import Rule, to_me
import nonebot

async def is_poke(event: Event) -> bool:
  return event.notice_type == "notify" and event.sub_type == "poke" and event.user_id != event.self_id

auto_repoke = nonebot.on_notice(Rule(is_poke) & to_me())

@auto_repoke.handle()
async def handle_auto_repoke(event: Event):
  await auto_repoke.send(MessageSegment("poke", {"qq": event.user_id}))
