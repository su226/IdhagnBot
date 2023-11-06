import re
from dataclasses import dataclass
from typing import Dict, Optional

import nonebot
from nonebot.message import event_preprocessor
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent, Message
from nonebot.exception import ActionFailed
from pydantic import BaseModel

from util import configs, context, hook, misc, permission


class Config(BaseModel):
  repeat_every: int = 2
  max_repeat: int = 1


@dataclass(frozen=True)
class LastMessage:
  message: Message
  received_count: int
  sent_count: int


last_messages: Dict[int, LastMessage] = {}
CONFIG = configs.SharedConfig("auto_repeat", Config)
ORIGINAL_EMOTE_RE = re.compile(r"^&#91;[A-Za-z0-9\u4e00-\u9fa5]+&#93;$")


@event_preprocessor
async def on_message_received(event: GroupMessageEvent) -> None:
  group_id = event.group_id
  last = last_messages.get(group_id)
  if last and is_same(event.message, last.message):
    last_messages[group_id] = LastMessage(event.message, last.received_count + 1, last.sent_count)
  else:
    last_messages[group_id] = LastMessage(event.message, 1, 0)


@hook.on_message_sent
async def on_message_sent(
  event: Optional[Event], is_group: bool, target_id: int, message: Message, message_id: int
) -> None:
  if not is_group:
    return
  last = last_messages.get(target_id)
  if last and is_same(message, last.message):
    last_messages[target_id] = LastMessage(message, last.received_count, last.sent_count + 1)
  else:
    last_messages[target_id] = LastMessage(message, 0, 1)


def is_original_emote(msg: Message) -> bool:
  # 找不到更好的解决方案，只能正则表达式匹配，虽然理论上不会漏判，但是会误判
  return ORIGINAL_EMOTE_RE.match(str(msg)) is not None


def is_same(msg1: Message, msg2: Message) -> bool:
  if msg1 is msg2:
    return True
  if len(msg1) != len(msg2):
    return False
  for seg1, seg2 in zip(msg1, msg2):
    if seg1.type != seg2.type:
      return False
    if seg1.type == "image":
      if seg1.data["file"] != seg2.data["file"]:
        return False
    elif seg1.data != seg2.data:
      return False
  return True


async def can_repeat(event: GroupMessageEvent) -> bool:
  if (last := last_messages.get(event.group_id)) and is_same(last.message, event.message):
    config = CONFIG()
    return (
      last.sent_count < last.received_count // config.repeat_every
      and last.sent_count < config.max_repeat
      and not misc.is_command(event.message)
      and not is_original_emote(event.message)
    )
  return False
auto_repeat = nonebot.on_message(
  can_repeat,
  context.build_permission(("auto_repeat", "can_repeat"), permission.Level.MEMBER),
  priority=2
)
@auto_repeat.handle()
async def handle_auto_repeat(event: GroupMessageEvent):
  for seg in event.message:
    if seg.type == "image":
      seg.data["file"] = seg.data["url"]
      del seg.data["url"]
  try:
    await auto_repeat.finish(event.message)
  except ActionFailed:
    pass
