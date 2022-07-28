import re

import nonebot
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import Rule

from util import context

last_message: dict[int, str] = {}
repeated: set[int] = set()
ORIGINAL_EMOTE_RE = re.compile(r"^&#91;[A-Za-z0-9\u4e00-\u9fa5]+&#93;$")


def is_command(event: MessageEvent) -> bool:
  return event.message.extract_plain_text().lstrip().startswith("/")


def is_original_emote(event: MessageEvent) -> bool:
  # 找不到更好的解决方案，只能正则表达式匹配，虽然理论上不会漏判，但是会误判
  return ORIGINAL_EMOTE_RE.match(str(event.message)) is not None


async def can_repeat(event: MessageEvent) -> bool:
  ctx = context.get_event_context(event)
  result = False
  if event.raw_message == last_message.get(ctx, None):
    result = ctx not in repeated and not (is_command(event) or is_original_emote(event))
  elif ctx in repeated:
    repeated.remove(ctx)
  last_message[ctx] = event.raw_message
  return result

auto_repeat = nonebot.on_message(Rule(can_repeat), priority=2)


@auto_repeat.handle()
async def handle_auto_repeat(event: MessageEvent):
  for seg in event.message:
    if seg.type == "image":
      seg.data["file"] = seg.data["url"]
  await auto_repeat.send(event.message)
  repeated.add(context.get_event_context(event))
