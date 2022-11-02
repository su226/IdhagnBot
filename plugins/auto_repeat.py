import re
from contextvars import ContextVar

import nonebot
from nonebot.adapters.onebot.v11 import Event, Message, MessageEvent
from nonebot.rule import Rule

from util import context, hook, util

suppress = ContextVar("suppress", default=False)
last_message: dict[int, tuple[Message, int]] = {}
ORIGINAL_EMOTE_RE = re.compile(r"^&#91;[A-Za-z0-9\u4e00-\u9fa5]+&#93;$")


@hook.on_message_sent
async def on_message_sent(
  event: Event | None, is_group: bool, target_id: int, message: Message, message_id: int
) -> None:
  if is_group and target_id in last_message and not suppress.get():
    del last_message[target_id]


def is_original_emote(event: MessageEvent) -> bool:
  # 找不到更好的解决方案，只能正则表达式匹配，虽然理论上不会漏判，但是会误判
  return ORIGINAL_EMOTE_RE.match(str(event.message)) is not None


def is_same(msg1: Message, msg2: Message) -> bool:
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


async def can_repeat(event: MessageEvent) -> bool:
  ctx = context.get_event_context(event)
  if ctx in last_message and is_same(event.message, last_message[ctx][0]):
    count = last_message[ctx][1] + 1
    last_message[ctx] = (event.message, count)
    result = count == 2 and not (util.is_command(event.message) or is_original_emote(event))
  else:
    last_message[ctx] = (event.message, 1)
    result = False
  return result
auto_repeat = nonebot.on_message(Rule(can_repeat), priority=2)
@auto_repeat.handle()
async def handle_auto_repeat(event: MessageEvent):
  for seg in event.message:
    if seg.type == "image":
      seg.data["file"] = seg.data["url"]
      del seg.data["url"]
  token = suppress.set(True)
  try:
    await auto_repeat.send(event.message)
  finally:
    suppress.reset(token)
