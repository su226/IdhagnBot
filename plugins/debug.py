from copy import deepcopy
from pprint import pformat

import yaml
from loguru import logger
from nonebot.adapters.onebot.v11 import (
  Bot, GroupMessageEvent, Message, MessageEvent, PrivateMessageEvent,
)
from nonebot.exception import ActionFailed
from nonebot.message import handle_event
from nonebot.params import CommandArg

from util import command, configs, context, misc


def get_message(msg: Message) -> str:
  texts = []
  for seg in msg:
    texts.append(seg.data["text"] if seg.is_text() else str(seg))
  return "".join(texts).replace("\r", "")


async def send(bot: Bot, event: MessageEvent, msg: Message):
  ctx = context.get_event_context(event)
  real_ctx = getattr(event, "group_id", -1)
  if ctx == -1:
    await bot.send_private_msg(user_id=event.user_id, message=msg)
  else:
    await bot.send_group_msg(group_id=ctx, message=msg)
  return real_ctx != ctx


async def redirect(bot: Bot, event: MessageEvent, msg: Message):
  ctx = context.get_event_context(event)
  real_ctx = getattr(event, "group_id", -1)
  if ctx == -1:
    await handle_event(bot, PrivateMessageEvent(
      time=event.time,
      self_id=event.self_id,
      post_type="message",
      # MessageEvent
      sub_type="normal",
      user_id=event.user_id,
      message_type="private",
      message_id=-1,
      message=msg,
      original_message=deepcopy(msg),
      raw_message=str(msg),
      font=event.font,
      sender=event.sender,
      to_me=True,
      reply=event.reply))
  else:
    await handle_event(bot, GroupMessageEvent(
      time=event.time,
      self_id=event.self_id,
      post_type="message",
      # MessageEvent
      sub_type="normal",
      user_id=event.user_id,
      message_type="group",
      message_id=-1,
      message=msg,
      original_message=deepcopy(msg),
      raw_message=str(msg),
      font=event.font,
      sender=event.sender,
      to_me=True,
      reply=event.reply,
      # GroupMessageEvent
      group_id=ctx,
      anonymous=getattr(event, "anonymous", None)))
  return real_ctx != ctx

api = (
  command.CommandBuilder("debug.api", "api")
  .level("super")
  .brief("调试机器人API")
  .usage('''\
/api <接口> [YAML数据]
YAML数据可换行
结果请在日志中查看''')
  .build())


@api.handle()
async def handle_api(bot: Bot, raw_arg: Message = CommandArg()):
  args = get_message(raw_arg).split(None, 1)
  if len(args) == 0:
    await api.finish("/api <接口> [YAML数据]")
  name = args[0]
  if len(args) == 1:
    data = {}
  else:
    try:
      data = yaml.load(args[1], configs.SafeLoader)
    except yaml.YAMLError as e:
      await api.finish(f"YAML无效: {e}")
  logger.info(f"执行 {name}: {pformat(data)}")
  try:
    result = await bot.call_api(name, **data)
  except ActionFailed:
    logger.exception(f"执行 {name} 失败:")
    await api.finish("执行失败")
  else:
    logger.success(f"执行 {name} 成功: {pformat(result)}")
    await api.finish("执行成功")

say = (
  command.CommandBuilder("debug.say", "发送", "say", "s")
  .level("super")
  .brief("发送普通消息")
  .usage('''\
/发送 <消息>
将会发送到当前上下文''')
  .build())


@say.handle()
async def handle_say(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
  if await send(bot, event, msg):
    name = context.CONFIG().groups[context.get_event_context(event)]._name
    await say.finish(f"已发送至 {name}")

raw = (
  command.CommandBuilder("debug.raw", "原始", "raw", "r")
  .level("super")
  .brief("发送含CQ码的消息")
  .usage('''\
/发送原始 <富文本消息>
将会发送到当前上下文''')
  .build())


@raw.handle()
async def handle_tellraw(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
  if await send(bot, event, Message(get_message(msg))):
    name = context.CONFIG().groups[context.get_event_context(event)]._name
    await raw.finish(f"已发送至 {name}")

execute = (
  command.CommandBuilder("debug.execute", "执行", "execute", "x")
  .level("super")
  .brief("在群内执行命令")
  .usage('''\
/执行 <命令名> [参数]
命令名可以不带斜线
相当于在当前上下文执行命令''')
  .build())


@execute.handle()
async def handle_execute(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
  if not misc.is_command(msg):
    msg[0].data["text"] = misc.command_start() + msg[0].data["text"]
  if await redirect(bot, event, msg):
    name = context.CONFIG().groups[context.get_event_context(event)]._name
    await execute.finish(f"已在 {name} 中执行命令")

reload = (
  command.CommandBuilder("debug.reload", "重载", "reload")
  .level("super")
  .brief("热重载支持的配置")
  .build())


@reload.handle()
async def handle_reload():
  for config in configs.BaseConfig.all:
    if config.reloadable:
      config.reload()
  await reload.finish("已重载所有配置")
