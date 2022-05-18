import asyncio
import random

from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg

from util import context, account_aliases, helper, command

super_poke = (command.CommandBuilder("super_poke", "戳亿戳", "poke")
  .in_group()
  .level("super")
  .brief("发送多次戳一戳")
  .usage("/戳亿戳 <总次数> <QQ号列表>")
  .build())
@super_poke.handle()
async def handle_super_poke(bot: Bot, event: Event, arg: Message = CommandArg()):
  ctx = context.get_event_context(event)
  args = arg.extract_plain_text().split()
  if len(args) < 2:
    await super_poke.send("/戳亿戳 <总次数> <QQ号列表>")
    return
  all_errors = []
  all_uids = []
  for pattern in args[1:]:
    try:
      all_uids.extend(await account_aliases.match_uid(bot, event, pattern, True))
    except helper.AggregateError as e:
      all_errors.extend(e)
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
