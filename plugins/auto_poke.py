from util import context, account_aliases
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.rule import Rule
from nonebot.params import CommandArg
import nonebot

def try_int(value: str) -> str | int:
  try:
    return int(value)
  except:
    return value

uids: dict[int, set[str]] = {}

auto_poke = nonebot.on_command("自动戳", context.in_context_rule(context.ANY_GROUP), {"autopoke"}, permission=context.Permission.SUPER)
auto_poke.__cmd__ = ["自动戳", "autopoke"]
auto_poke.__brief__ = "查看、设置和清除自动戳"
auto_poke.__doc__ = '''\
/自动戳 - 查看自动戳
/自动戳 <QQ号列表> - 设置自动戳
/自动戳 clear|清除 - 清除自动戳'''
auto_poke.__perm__ = context.Permission.SUPER
auto_poke.__ctx__ = context.ANY_GROUP
@auto_poke.handle()
async def handle_auto_poke(bot: Bot, event: Event, args: Message = CommandArg()):
  ctx = context.get_event_context(event)
  args = str(args).split()
  if len(args) == 0:
    await auto_poke.send("当前自动戳：\n" + "\n".join(uids[ctx]))
  elif args == ["clear"] or args == ["清除"]:
    if ctx in uids:
      del uids[ctx]
    await auto_poke.send("已清除自动戳")
  else:
    errors = []
    all_uids = []
    aliases = await account_aliases.get_aliases(bot, event)
    for pattern in args:
      try:
        all_uids = int(pattern)
        continue
      except: pass
      try:
        all_uids.extend(account_aliases.try_match(aliases, pattern, True))
      except account_aliases.MatchException as e:
        errors.extend(e.errors)
    if len(errors):
      await auto_poke.send("\n".join(errors))
      return
    uids[ctx] = all_uids
    await auto_poke.send("已设置自动戳：\n" + "\n".join(map(str, uids[ctx])))

async def has_uid(event: Event) -> bool:
  return event.user_id in uids.get(context.get_event_context(event), [])

do_auto_poke = nonebot.on_message(Rule(has_uid), priority=2)

@do_auto_poke.handle()
async def do_handle_auto_poke(event: Event):
  await do_auto_poke.send(MessageSegment("poke", {"qq": event.user_id}))
