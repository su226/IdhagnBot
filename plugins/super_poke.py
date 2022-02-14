from core_plugins.context.typing import Context
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg
import random
import nonebot

context: Context = nonebot.require("context")
account_aliases = nonebot.require("account_aliases")

super_poke = nonebot.on_command("戳亿戳", context.in_context_rule(context.ANY_GROUP), {"poke", "superpoke"}, permission=context.SUPER)
super_poke.__cmd__ = ["戳亿戳", "poke", "superpoke"]
super_poke.__brief__ = "发送多次戳一戳"
super_poke.__doc__ = "/戳亿戳 <总次数> <QQ号列表>"
super_poke.__ctx__ = context.ANY_GROUP
super_poke.__perm__ = context.SUPER
@super_poke.handle()
async def handle_super_poke(bot: Bot, event: Event, args: Message = CommandArg()):
  ctx = context.get_context(event)
  args = str(args).split()
  if len(args) < 2:
    await super_poke.send("/戳亿戳 <总次数> <QQ号列表>")
    return
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
    await super_poke.send("\n".join(e.errors))
    return
  cur_uids = []
  await super_poke.send("戳亿戳开始")
  for _ in range(int(args[0])):
    if len(cur_uids) == 0:
      cur_uids = all_uids[:]
      random.shuffle(cur_uids)
    await bot.call_api("send_group_msg",
      group_id=ctx,
      message=f"[CQ:poke,qq={cur_uids.pop()}]")
  await super_poke.send("戳亿戳完成")
