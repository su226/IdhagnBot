from util import context
from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.rule import Rule
import nonebot
import re

last_message: dict[int, Message] = {}
repeated: set[int] = set()

def is_command(event: MessageEvent) -> bool:
  return event.message.extract_plain_text().lstrip().startswith("/")

ORIGINAL_EMOTE_RE = re.compile(r"^\[[A-Za-z0-9\u4e00-\u9fa5]+\]$")
def is_original_emote(event: MessageEvent) -> bool:
  # 找不到更好的解决方案，只能正则表达式匹配，虽然理论上不会漏判，但是会误判
  return ORIGINAL_EMOTE_RE.match(event.raw_message)

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
