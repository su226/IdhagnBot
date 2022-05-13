from util import context, account_aliases
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg
import asyncio
import random
import nonebot

super_poke = nonebot.on_command("戳亿戳", context.in_group_rule(context.ANY_GROUP), {"poke", "superpoke"}, permission=context.Permission.SUPER)
super_poke.__cmd__ = ["戳亿戳", "poke", "superpoke"]
super_poke.__brief__ = "发送多次戳一戳"
super_poke.__doc__ = "/戳亿戳 <总次数> <QQ号列表>"
super_poke.__ctx__ = context.ANY_GROUP
super_poke.__perm__ = context.Permission.SUPER
@super_poke.handle()
async def handle_super_poke(bot: Bot, event: Event, args: Message = CommandArg()):
  ctx = context.get_event_context(event)
  args = str(args).split()
  if len(args) < 2:
    await super_poke.send("/戳亿戳 <总次数> <QQ号列表>")
    return
  all_errors = []
  all_uids = []
  for pattern in args[1:]:
    try:
      all_uids.append(int(pattern))
      continue
    except: pass
    errors, uids = await account_aliases.match_uid(bot, event, pattern, True)
    all_uids.extend(uids)
    all_errors.extend(errors)
  if len(all_errors):
    await super_poke.send("\n".join(all_errors))
    return
  cur_uids = []
  await super_poke.send("戳亿戳开始")
  coros = []
  for _ in range(int(args[0])):
    if len(cur_uids) == 0:
      cur_uids = all_uids[:]
      random.shuffle(cur_uids)
    coros.append(bot.send_group_msg(
      group_id=ctx,
      message=f"[CQ:poke,qq={cur_uids.pop()}]"))
  await asyncio.gather(*coros)
  await super_poke.send("戳亿戳完成")
