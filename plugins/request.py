import nonebot
from nonebot.adapters.onebot.v11 import (
  Bot, FriendRequestEvent, GroupIncreaseNoticeEvent, Message, MessageSegment, GroupRequestEvent,
)
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg

from util import misc, command


def check_group_increase(event: GroupIncreaseNoticeEvent) -> bool:
  return (
    event.user_id == event.self_id
    and event.sub_type == "invite"
    and not misc.is_superuser(event.operator_id)
  )

on_group_increase = nonebot.on_notice(check_group_increase)

@on_group_increase.handle()
async def handle_group_increase(bot: Bot, event: GroupIncreaseNoticeEvent) -> None:
  try:
    nickname = (await bot.get_stranger_info(user_id=event.user_id))["nickname"]
  except ActionFailed:
    nickname = "未知"
  try:
    group_name = (await bot.get_group_info(group_id=event.group_id))["group_name"]
  except ActionFailed:
    group_name = "未知"
  message = Message(MessageSegment.text(
    f"{nickname}({event.operator_id}) 已将 IdhagnBot 拉入 {group_name}({event.group_id})，"
    "请及时配置上下文",
  ))
  for superuser in misc.superusers():
    await bot.send_private_msg(user_id=superuser, message=message)


def check_friend_request(event: FriendRequestEvent) -> bool:
  return True

on_friend_request = nonebot.on_request(check_friend_request)

@on_friend_request.handle()
async def handle_friend_request(bot: Bot, event: FriendRequestEvent) -> None:
  try:
    nickname = (await bot.get_stranger_info(user_id=event.user_id))["nickname"]
  except ActionFailed:
    nickname = "未知"
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
  await friend_approve.send("已接受加好友请求")


friend_reject = (
  command.CommandBuilder("request.friend_reject", "拒绝好友")
  .level("super")
  .build()
)

@friend_reject.handle()
async def handle_friend_reject(bot: Bot, args: Message = CommandArg()) -> None:
  flag = args.extract_plain_text().rstrip()
  await bot.set_friend_add_request(flag=flag, approve=False)
  await friend_reject.send("已拒绝加好友请求")

def check_group_request(event: GroupRequestEvent) -> bool:
  return event.sub_type == "invite"

on_group_request = nonebot.on_request(check_group_request)

@on_group_request.handle()
async def handle_group_request(bot: Bot, event: GroupRequestEvent) -> None:
  try:
    nickname = (await bot.get_stranger_info(user_id=event.user_id))["nickname"]
  except ActionFailed:
    nickname = "未知"
  try:
    group_name = (await bot.get_group_info(group_id=event.group_id))["group_name"]
  except ActionFailed:
    group_name = "未知"
  message = Message(MessageSegment.text(
    f"{nickname}({event.user_id}) 请求将 IdhagnBot 拉入群聊 {group_name}({event.group_id})\n"
    f"发送 /同意加群 {event.flag} 同意请求，发送 /拒绝加群 {event.flag} 拒绝请求",
  ))
  for superuser in misc.superusers():
    await bot.send_private_msg(user_id=superuser, message=message)


group_approve = (
  command.CommandBuilder("request.group_approve", "同意加群")
  .level("super")
  .build()
)

@group_approve.handle()
async def handle_group_approve(bot: Bot, args: Message = CommandArg()) -> None:
  flag = args.extract_plain_text().rstrip()
  await bot.set_group_add_request(flag=flag, sub_type="invite", approve=True)
  await group_approve.send("已接受加群请求")


group_reject = (
  command.CommandBuilder("request.group_reject", "拒绝加群")
  .level("super")
  .build()
)

@group_reject.handle()
async def handle_group_reject(bot: Bot, args: Message = CommandArg()) -> None:
  flag = args.extract_plain_text().rstrip()
  await bot.set_group_add_request(flag=flag, sub_type="invite", approve=False)
  await group_reject.send("已拒绝加群请求")
