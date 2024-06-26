from typing import Dict, Set

import nonebot
from nonebot.adapters.onebot.v11 import (
  Bot, GroupDecreaseNoticeEvent, GroupIncreaseNoticeEvent, Message,
)
from pydantic import BaseModel, Field

from util import configs


class Config(BaseModel):
  welcome: Dict[int, str] = Field(default_factory=dict)
  leave: Set[int] = Field(default_factory=set)


CONFIG = configs.SharedConfig("welcome", Config)


async def check_welcome(event: GroupIncreaseNoticeEvent):
  return event.group_id in CONFIG().welcome
welcome = nonebot.on_notice(check_welcome)


@welcome.handle()
async def handle_welcome(event: GroupIncreaseNoticeEvent):
  await welcome.finish(Message(CONFIG().welcome[event.group_id].format(event.user_id)))


async def check_leave(event: GroupDecreaseNoticeEvent):
  return event.group_id in CONFIG().leave
leave = nonebot.on_notice(check_leave)


@leave.handle()
async def handle_leave(bot: Bot, event: GroupDecreaseNoticeEvent):
  username = (await bot.get_stranger_info(user_id=event.user_id))["nickname"]
  if event.operator_id != event.user_id:
    operator_name = (await bot.get_group_member_info(
      group_id=event.group_id, user_id=event.operator_id))["nickname"]
    await leave.finish(
      f"{operator_name}（{event.operator_id}）将 {username}（{event.user_id}）踢出了本群")
  else:
    await leave.finish(f"{username}（{event.user_id}）退出了本群")
