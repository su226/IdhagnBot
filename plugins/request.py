import nonebot
from nonebot.adapters.onebot.v11 import (
  Bot, FriendRequestEvent, GroupIncreaseNoticeEvent, Message, MessageSegment,
)
from nonebot.params import CommandArg

from util import misc, command


def check_group_increase(event: GroupIncreaseNoticeEvent) -> bool:
  return (
    event.user_id == event.self_id
    and event.sub_type == "invite"
    and not misc.is_superuser(event.operator_id)
  )

on_group_increase = nonebot.on_notice(check_group_increase)

async def handle_group_increase(bot: Bot, event: GroupIncreaseNoticeEvent) -> None:
  nickname = (await bot.get_stranger_info(user_id=event.operator_id))["nickname"]
  group_name = (await bot.get_group_info(group_id=event.group_id))["group_name"]
  message = Message(MessageSegment.text(
    f"{nickname}({event.operator_id}) 已将 IdhagnBot 拉入 {group_name}({event.group_id})，"
    "请及时配置上下文",
  ))
  for superuser in misc.superusers():
    await bot.send_private_msg(user_id=superuser, message=message)


def check_friend_request(event: FriendRequestEvent) -> bool:
  return True

on_friend_request = nonebot.on_request(check_friend_request)

async def handle_friend_request(bot: Bot, event: FriendRequestEvent) -> None:
  nickname = (await bot.get_stranger_info(user_id=event.user_id))["nickname"]
  message = Message(MessageSegment.text(
    f"{nickname}({event.user_id}) 请求添加 IdhagnBot 为好友，验证消息：{event.comment}\n"
    f"发送 /同意好友 {event.flag} 同意请求，发送 /拒绝好友 {event.flag} 拒绝请求",
  ))
  for superuser in misc.superusers():
    await bot.send_private_msg(user_id=superuser, message=message)


friend_approve = (
  command.CommandBuilder("request.friend_approve", "同意好友")
  .level("super")
  .build()
)

@friend_approve.handle()
async def handle_friend_approve(bot: Bot, args: Message = CommandArg()) -> None:
  flag = args.extract_plain_text().rstrip()
  await bot.set_friend_add_request(flag=flag, approve=True)


friend_reject = (
  command.CommandBuilder("request.friend_reject", "拒绝好友")
  .level("super")
  .build()
)

@friend_reject.handle()
async def handle_friend_reject(bot: Bot, args: Message = CommandArg()) -> None:
  flag = args.extract_plain_text().rstrip()
  await bot.set_friend_add_request(flag=flag, approve=False)
