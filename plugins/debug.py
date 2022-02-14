from core_plugins.context.typing import Context
from pprint import pformat
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message, GroupMessageEvent
from nonebot.params import CommandArg
from nonebot.message import handle_event
import nonebot
import yaml

context: Context = nonebot.require("context")
account_aliases = nonebot.require("account_aliases")
def get_message(msg: Message) -> str:
  texts = []
  for seg in msg:
    texts.append(seg.data["text"] if seg.is_text() else str(seg))
  return "".join(texts).replace("\r", "")

api = nonebot.on_command("api", permission=context.SUPER)
api.__cmd__ = "api"
api.__brief__ = "调试机器人API"
api.__doc__ = '''\
/api <接口> [YAML数据]
YAML数据可换行
结果请在日志中查看'''
api.__perm__ = context.SUPER
@api.handle()
async def handle_api(bot: Bot, args: Message = CommandArg()):
  args = get_message(args).split(None, 1)
  if len(args) == 0:
    await api.send("/api <接口> [YAML数据]")
    return
  name = args[0]
  if len(args) == 1:
    data = {}
  else:
    try:
      data = yaml.load(args[1], yaml.CLoader)
    except yaml.YAMLError as e:
      await api.send(f"YAML无效: {e}")
      return
  logger.info(f"执行 {name}: {pformat(data)}")
  try:
    result = await bot.call_api(name, **data)
  except:
    logger.exception(f"执行 {name} 失败:")
    await api.send("执行失败")
  else:
    logger.success(f"执行 {name} 成功: {pformat(result)}")
    await api.send("执行成功")

say = nonebot.on_command("发送", aliases={"say", "s"}, permission=context.SUPER)
say.__cmd__ = ["发送", "say", "s"]
say.__brief__ = "发送富文本消息"
say.__doc__ = '''\
/发送 <富文本消息>
将会发送到当前上下文'''
say.__perm__ = context.SUPER
@say.handle()
async def handle_say(bot: Bot, event: Event, msg: Message = CommandArg()):
  real_ctx = event.group_id if hasattr(event, "group_id") else -1
  ctx = context.get_context(event)
  if real_ctx == ctx:
    await say.send(msg)
  else:
    await bot.send_group_msg(group_id=ctx, message=msg)
    await say.send(f"已发送至 {context.get_group_name(ctx)}")

match = nonebot.on_command("匹配", aliases={"match"})
match.__cmd__ = ["匹配", "match"]
match.__brief__ = "从名字匹配群成员"
match.__doc__ = '''\
/匹配 <昵称、群名片或别名>
只接受中文、英文和数字
不能有空格，不区分大小写
特殊符号、emoji等会被忽略'''
@match.handle()
async def handle_match(bot: Bot, event: Event, args: Message = CommandArg()):
  name = str(args).rstrip()
  if " " in args:
    await match.send("不能有空格")
    return
  pattern = account_aliases.to_identifier(name)
  if not pattern:
    await match.send("有效名字为空，运行 /帮助 匹配 查看详情")
    return
  aliases = await account_aliases.get_aliases(bot, event)
  all, _, _ = account_aliases.match(aliases, pattern)
  limit = 10
  segments = []
  if len(all) == 0:
    segments.append(f"找不到 {pattern}")
  else:
    segments.append(f"{pattern} 可以指：")
  if len(all) > limit:
    for _, i in zip(range(limit - 1), all.values()):
      segments.append(f"{i}（{'、'.join(map(str, i.items))}）")
    segments.append(f"等 {len(all)} 个成员或别名")
  else:
    for i in all.values():
      segments.append(f"{i}（{'、'.join(map(str, i.items))}）")
  await match.send("\n".join(segments))

execute = nonebot.on_command("执行", context.in_context_rule(context.ANY_GROUP), {"execute", "x"}, permission=context.SUPER)
execute.__cmd__ = ["执行", "execute", "x"]
execute.__brief__ = "在群内执行命令"
execute.__doc__ = '''\
/执行 <命令名> [参数]
命令名不能带斜线
相当于在当前上下文执行命令'''
execute.__ctx__ = context.ANY_GROUP
execute.__perm__ = context.SUPER
@execute.handle()
async def handle_execute(bot: Bot, event: Event, msg: Message = CommandArg()):
  ctx = context.get_context(event)
  msg[0].data["text"] = "/" + msg[0].data["text"]
  await handle_event(bot, GroupMessageEvent(
    time=event.time,
    self_id=event.self_id,
    post_type="message",
    sub_type="normal",
    user_id=event.user_id,
    message_type="group",
    message_id=event.message_id,
    message=msg,
    raw_message=str(msg),
    font=event.font,
    sender=event.sender,
    group_id=ctx))
  await execute.send(f"已在 {context.get_group_name(ctx)} 中执行命令")

sayexecute = nonebot.on_command("发送执行", context.in_context_rule(context.ANY_GROUP), {"sayexecute", "sx"}, permission=context.SUPER)
sayexecute.__cmd__ = ["发送执行", "sayexecute", "sx"]
sayexecute.__brief__ = "在群内发送并执行命令"
sayexecute.__doc__ = '''\
/发送执行 <命令名> [参数]
命令名不能带斜线
相当于先执行 "/发送 /命令名 参数"
再执行 "/执行 命令名 参数"'''
sayexecute.__ctx__ = context.ANY_GROUP
sayexecute.__perm__ = context.SUPER
@sayexecute.handle()
async def handle_sayexecute(bot: Bot, event: Event, msg: Message = CommandArg()):
  ctx = context.get_context(event)
  msg[0].data["text"] = "/" + msg[0].data["text"]
  await bot.send_group_msg(group_id=ctx, message=msg)
  await handle_event(bot, GroupMessageEvent(
    time=event.time,
    self_id=event.self_id,
    post_type="message",
    sub_type="normal",
    user_id=event.user_id,
    message_type="group",
    message_id=event.message_id,
    message=msg,
    raw_message=str(msg),
    font=event.font,
    sender=event.sender,
    group_id=ctx))
  await sayexecute.send(f"已在 {context.get_group_name(ctx)} 中发送并执行命令")

batch = nonebot.on_command("批量", context.in_context_rule(context.ANY_GROUP), {"batch"}, permission=context.SUPER)
batch.__cmd__ = ["批量", "batch"]
batch.__brief__ = "依次执行多条命令"
batch.__doc__ = '''\
/批量 <一行一个命令>
命令名不能带斜线
相当于依次发送多次 /执行"'''
batch.__ctx__ = context.ANY_GROUP
batch.__perm__ = context.SUPER
@batch.handle()
async def handle_batch(bot: Bot, event: Event, msg: Message = CommandArg()):
  ctx = context.get_context(event)
  for command in get_message(msg).split("\n"):
    command = "/" + command
    await handle_event(bot, GroupMessageEvent(
      time=event.time,
      self_id=event.self_id,
      post_type="message",
      sub_type="normal",
      user_id=event.user_id,
      message_type="group",
      message_id=event.message_id,
      message=Message(command),
      raw_message=command,
      font=event.font,
      sender=event.sender,
      group_id=ctx))
