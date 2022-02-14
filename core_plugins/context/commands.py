from .config import CONFIG
from .core import enter_context, get_context, get_event_context, refresh_context, exit_context, in_context_rule, PRIVATE, ANY_GROUP
from nonebot.adapters.onebot.v11 import Bot, Event, PrivateMessageEvent
from nonebot.exception import IgnoredException
from nonebot.message import event_preprocessor
from nonebot.params import CommandArg
import nonebot

group_to_name = {}
group_to_aliases = {}
alias_to_group = {}
for group, aliases in CONFIG.groups.items():
  group_to_name[group] = f"未知_{group}"
  group_to_aliases[group] = aliases
  for j in aliases:
    alias_to_group[j] = group

driver = nonebot.get_driver()
@driver.on_bot_connect
async def bot_connect(bot: Bot):
  for info in await bot.call_api("get_group_list"):
    if info["group_id"] in group_to_name:
      group_to_name[info["group_id"]] = info["group_name"]

aliases = nonebot.on_command("别名", in_context_rule(ANY_GROUP), {"alias", "aliases"})
aliases.__cmd__ = ["别名", "alias", "aliases"]
aliases.__brief__ = "查看当前群聊上下文的别名"
aliases.__ctx__ = [ANY_GROUP]
@aliases.handle()
async def handle_aliases(event: Event):
  await aliases.send("当前群聊上下文有以下别名:\n" + ", ".join(group_to_aliases[get_event_context(event)]))

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
    ctx = get_context(uid)
    if ctx == PRIVATE:
      await context.send("当前为私聊上下文")
    else:
      info = await bot.call_api("get_group_info", group_id=ctx)
      await context.send(f"当前为 {info['group_name']}（{ctx}）的群聊上下文")
    return
  elif args in (str(PRIVATE), "退出", "私聊", "exit"):
    if exit_context(uid):
      await context.send("已退出群聊上下文")
    else:
      await context.send("未进入群聊上下文")
    return
  try:
    gid = int(args)
  except:
    if args in alias_to_group:
      gid = alias_to_group[args]
    else:
      await context.send(error_str)
      return
  if not gid in group_to_name:
    await context.send(error_str)
    return
  try:
    await bot.call_api("get_group_member_info", group_id=gid, user_id=uid)
  except:
    await context.send(error_str)
    return
  enter_context(uid, gid)
  await context.send(f"已进入 {group_to_name[gid]}（{gid}）的群聊上下文")

@event_preprocessor
async def pre_event(event: Event):
  if hasattr(event, "group_id"):
    if event.group_id not in group_to_name or event.user_id == ***REMOVED***:
      raise IgnoredException("机器人在当前上下文不可用")
  elif hasattr(event, "user_id"):
    refresh_context(event.user_id)
