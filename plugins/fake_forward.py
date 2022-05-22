import asyncio

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg

from util import account_aliases, command, helper


async def get_card(bot: Bot, group: int, user: int) -> str:
  try:
    info = await bot.get_group_member_info(group_id=group, user_id=user)
  except ActionFailed:
    return (await bot.get_stranger_info(user_id=user))["nickname"]
  else:
    return info["card"] or info["nickname"]

fake_forward = (
  command.CommandBuilder("fake_forward", "我有一个朋友", "朋友", "吾有一友", "friend")
  .brief("鲁迅：我没有说过这句话")
  .usage("/我有一个朋友 <用户> <消息>")
  .private(False)
  .build())


@fake_forward.handle()
async def handle_fake_forward(bot: Bot, event: GroupMessageEvent, msg: Message = CommandArg()):
  args = str(msg).split(None, 1)
  if len(args) != 2:
    await fake_forward.finish(fake_forward.__doc__)
  try:
    uid = await account_aliases.match_uid(bot, event, args[0])
  except helper.AggregateError as e:
    await fake_forward.finish("\n".join(e))
  card, bot_card = await asyncio.gather(
    get_card(bot, event.group_id, uid),
    get_card(bot, event.group_id, event.self_id))
  await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=[
    {
      "type": "node",
      "data": {
        "name": card,
        "uin": uid,
        "content": args[1]
      }
    },
    {
      "type": "node",
      "data": {
        "name": bot_card,
        "uin": event.self_id,
        "content": "免责声明：本消息由机器人发送，仅供娱乐，切勿当真！"
      }
    },
  ])
