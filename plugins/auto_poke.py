import nonebot
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from nonebot.rule import Rule

from util import command, context, misc, user_aliases

uids: dict[int, set[str]] = {}

auto_poke = (
  command.CommandBuilder("auto_poke", "自动戳")
  .level("super")
  .in_group()
  .brief("查看、设置和清除自动戳")
  .usage('''\
/自动戳 - 查看自动戳
/自动戳 <QQ号列表> - 设置自动戳
/自动戳 clear|清除 - 清除自动戳''')
  .build())


@auto_poke.handle()
async def handle_auto_poke(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
  ctx = context.get_event_context(event)
  args = arg.extract_plain_text().split()
  if len(args) == 0:
    await auto_poke.finish("当前自动戳：\n" + "\n".join(map(str, uids.get(ctx, []))))
  elif args == ["clear"] or args == ["清除"]:
    if ctx in uids:
      del uids[ctx]
    await auto_poke.finish("已清除自动戳")
  else:
    all_errors = []
    all_uids = []
    for pattern in args:
      try:
        all_uids.extend(await user_aliases.match_uid(bot, event, pattern, True))
      except misc.AggregateError as e:
        all_errors.extend(e)
    if all_errors:
      await auto_poke.finish("\n".join(all_errors))
    uids[ctx] = set(all_uids)
    await auto_poke.finish("已设置自动戳：\n" + "\n".join(map(str, uids[ctx])))


async def has_uid(event: MessageEvent) -> bool:
  return event.user_id in uids.get(context.get_event_context(event), [])

do_auto_poke = nonebot.on_message(Rule(has_uid), priority=2)


@do_auto_poke.handle()
async def do_handle_auto_poke(event: MessageEvent):
  await do_auto_poke.finish(MessageSegment("poke", {"qq": event.user_id}))
