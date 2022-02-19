from util.context import enter_context, get_event_context, get_event_context, exit_context, in_context_rule, PRIVATE, ANY_GROUP, GROUP_IDS, GROUP_NAMES
from nonebot.adapters.onebot.v11 import Bot, Event, PrivateMessageEvent
from nonebot.params import CommandArg
import nonebot

aliases = nonebot.on_command("别名", in_context_rule(ANY_GROUP), {"alias", "aliases"})
aliases.__cmd__ = ["别名", "alias", "aliases"]
aliases.__brief__ = "查看当前群聊上下文的别名"
aliases.__ctx__ = [ANY_GROUP]
@aliases.handle()
async def handle_aliases(event: Event):
  await aliases.send("当前群聊上下文有以下别名:\n" + ", ".join(GROUP_IDS[get_event_context(event)].aliases))

error_str = "无效的群号或别名、你不是该群的成员，或机器人在该群不可用"
context = nonebot.on_command("上下文", aliases={"context", "ctx"})
context.__cmd__ = ["上下文", "context", "ctx"]
context.__brief__ = "进入或退出上下文"
context.__priv__ = True
context.__doc__ = '''\
{cmd} - 查看当前上下文
{cmd} <群号或别名> - 进入群聊上下文
{cmd} 退出 - 退出群聊上下文'''
@context.handle()
async def handle_context(bot: Bot, event: PrivateMessageEvent, args = CommandArg()):
  args: str = str(args).rstrip()
  uid = event.user_id
  if args == "":
    ctx = get_event_context(uid)
    if ctx == PRIVATE:
      await context.finish("当前为私聊上下文")
    else:
      await context.finish(f"当前为 {GROUP_IDS[ctx].name}（{ctx}）的群聊上下文")
  elif args in (str(PRIVATE), "退出", "私聊", "exit"):
    if exit_context(uid):
      await context.finish("已退出群聊上下文")
    else:
      await context.finish("未进入群聊上下文")
  try:
    gid = int(args)
  except:
    if args in GROUP_NAMES:
      gid = GROUP_NAMES[args]
    else:
      await context.finish(error_str)
  else:
    if not gid in GROUP_IDS:
      await context.finish(error_str)
  try:
    await bot.call_api("get_group_member_info", group_id=gid, user_id=uid)
  except:
    await context.finish(error_str)
  enter_context(uid, gid)
  await context.send(f"已进入 {GROUP_IDS[gid].name}（{gid}）的群聊上下文")
