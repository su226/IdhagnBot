import nonebot
from nonebot.adapters.onebot.v11 import Bot, Event, Message, NoticeEvent, PrivateMessageEvent
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg

from util import command
from util.context import (
  ANY_GROUP, CONFIG, PRIVATE, STATE, enter_context, exit_context, get_event_context,
)


async def check_invaildate(event: NoticeEvent) -> bool:
  return event.notice_type in {"group_increase", "group_decrease"}
invaildate = nonebot.on_notice(check_invaildate)
@invaildate.handle()
async def handle_invaildate(event: NoticeEvent) -> None:
  group_id: int = getattr(event, "group_id")
  state = STATE()
  if group_id in state._has_group_cache:
    state._has_group_cache[group_id].clear()


alias = (
  command.CommandBuilder("context.alias", "别名", "alias")
  .in_group(ANY_GROUP)
  .brief("查看当前群聊上下文的别名")
  .build()
)
@alias.handle()
async def handle_alias(event: Event):
  config = CONFIG()
  aliases = config.groups[get_event_context(event)].root
  await alias.finish("当前群聊上下文有以下别名:\n" + ", ".join(aliases))


error_str = "无效的群号或别名、你不是该群的成员，或机器人在该群不可用"
context = (
  command.CommandBuilder("context.ctx", "上下文", "ctx")
  .brief("进入或退出上下文")
  .usage('''\
/上下文 - 查看当前上下文
/上下文 <群号或别名> - 进入群聊上下文
/上下文 退出|exit - 退出群聊上下文''')
  .private(True)
  .build()
)
@context.handle()
async def handle_context(bot: Bot, event: PrivateMessageEvent, arg: Message = CommandArg()):
  config = CONFIG()
  args = arg.extract_plain_text().rstrip()
  uid = event.user_id
  if args == "":
    ctx = get_event_context(event)
    if ctx == PRIVATE:
      await context.finish("当前为私聊上下文")
    else:
      name = config.groups[ctx]._name
      await context.finish(f"当前为 {name}（{ctx}）的群聊上下文")
  elif args in (str(PRIVATE), "退出", "私聊", "exit"):
    if exit_context(uid):
      await context.finish("已退出群聊上下文")
    else:
      await context.finish("未进入群聊上下文")
  try:
    gid = int(args)
  except ValueError:
    if args in config._names:
      gid = config._names[args]
    else:
      await context.finish(error_str)
  else:
    if gid not in config.groups:
      await context.finish(error_str)
  try:
    await bot.get_group_member_info(group_id=gid, user_id=uid)
  except ActionFailed:
    await context.finish(error_str)
  enter_context(uid, gid)
  name = config.groups[gid]._name
  await context.finish(f"已进入 {name}（{gid}）的群聊上下文")
