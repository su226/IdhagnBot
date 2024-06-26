from argparse import Namespace
from datetime import datetime, timedelta
from typing import Dict, Set, Tuple

import nonebot
from nonebot.adapters.onebot.v11 import GROUP_MEMBER, Bot, Message, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed
from nonebot.params import EventMessage, ShellCommandArgs
from nonebot.permission import SUPERUSER
from nonebot.rule import ArgumentParser
from nonebot.typing import T_State
from pydantic import BaseModel, Field

from util import command, configs, context, misc

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402


class Config(BaseModel):
  ban_timeout: int = 60
  ban_thresold: int = 3
  ban_duration: int = 600
  show_word: bool = True
  show_ban: bool = True


class State(BaseModel):
  words: Set[str] = Field(default_factory=set)


CONFIG = configs.SharedConfig("forbidden_word", Config)
STATE = configs.GroupState("forbidden_word", State)
COUNT: Dict[Tuple[int, int], int] = {}

manage_parser = ArgumentParser("/屏蔽词", add_help=False)
subparsers = manage_parser.add_subparsers(required=True)
parser = subparsers.add_parser("查看", add_help=False)
parser.set_defaults(subcommand="view")
parser = subparsers.add_parser("添加", add_help=False)
parser.add_argument("words", nargs="+", metavar="词语")
parser.set_defaults(subcommand="add")
parser = subparsers.add_parser("删除", add_help=False)
parser.add_argument("words", nargs="+", metavar="词语")
parser.set_defaults(subcommand="delete")
manage = (
  command.CommandBuilder("forbidden_word.manage", "屏蔽词")
  .in_group()
  .level("admin")
  .shell(manage_parser)
  .brief("管理屏蔽词")
  .usage('''\
/屏蔽词 查看 - 列出所有屏蔽词
/屏蔽词 添加 <词语...> - 添加一个或多个屏蔽词
/屏蔽词 删除 <词语...> - 删除一个或多个屏蔽词''')
  .build())


@manage.handle()
async def handle_manage(event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  ctx = context.get_event_context(event)
  state = STATE(ctx)
  if args.subcommand == "view":
    words = "、".join(f'"{word}"' if '"' in word else word for word in state.words)
    await manage.finish("当前屏蔽词：" + words)
  elif args.subcommand == "add":
    old_len = len(state.words)
    state.words.update(args.words)
    new_len = len(state.words)
    added = new_len - old_len
    STATE.dump(ctx)
    await manage.finish(
      f"已添加{added}个，{len(args.words) - added}个之前已经添加，目前共有{new_len}个屏蔽词")
  elif args.subcommand == "delete":
    old_len = len(state.words)
    state.words.difference_update(args.words)
    new_len = len(state.words)
    removed = old_len - new_len
    STATE.dump(ctx)
    await manage.finish(
      f"已删除{removed}个，{len(args.words) - removed}个本就不存在，目前共有{new_len}个屏蔽词")


def decr_count(key: Tuple[int, int]):
  if COUNT[key] == 0:
    del COUNT[key]


async def check_recall(
  bot: Bot, event: MessageEvent, state: T_State, msg: Message = EventMessage(),
) -> bool:
  if await SUPERUSER(bot, event):
    return False
  str_msg = str(msg)
  ctx = context.get_event_context(event)
  for word in STATE(ctx).words:
    if word in str_msg:
      state["word"] = word
      return True
  return False
recall = nonebot.on_message(check_recall, GROUP_MEMBER)


@recall.handle()
async def handle_recall(event: MessageEvent, bot: Bot, state: T_State):
  try:
    await bot.delete_msg(message_id=event.message_id)
  except ActionFailed:
    return
  ctx = context.get_event_context(event)
  config = CONFIG()
  if "word" in state and config.show_word:
    prefix = f"请不要发送“{state['word']}”等违禁内容"
  else:
    prefix = "请不要发送违禁内容"
  if config.ban_timeout != 0 and config.ban_thresold != 0:
    key = (ctx, event.user_id)
    COUNT[key] = COUNT.get(key, 0) + 1
    scheduler.add_job(
      decr_count, "date", (key,), run_date=datetime.now() + timedelta(seconds=config.ban_timeout))
    if COUNT[key] >= config.ban_thresold:
      await bot.set_group_ban(group_id=ctx, user_id=event.user_id, duration=config.ban_duration)
      suffix = "，已禁言警告"
    elif config.show_ban:
      suffix = (
        f"，{misc.format_time(config.ban_timeout)}内发送超过{config.ban_thresold}条"
        f"将会禁言{misc.format_time(config.ban_duration)}警告")
    else:
      suffix = "，否则可能会禁言警告"
  else:
    suffix = ""
  await recall.finish(MessageSegment.at(event.user_id) + f"{prefix}{suffix}")
