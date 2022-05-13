from util import account_aliases
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.params import CommandArg
import nonebot
import asyncio

async def get_card(bot: Bot, group: int, user: int) -> str:
  try:
    info = await bot.get_group_member_info(group_id=group, user_id=user)
  except:
    return (await bot.get_stranger_info(user_id=user))["nickname"]
  else:
    return info["card"] or info["nickname"]

fake_forward = nonebot.on_command("我有一个朋友", aliases={"朋友", "吾有一友", "friend"})
fake_forward.__cmd__ = ["我有一个朋友", "朋友", "吾有一友", "friend"]
fake_forward.__brief__ = "鲁迅：我没有说过这句话"
fake_forward.__doc__ = "/我有一个朋友 <用户> <消息>"
fake_forward.__priv__ = False
@fake_forward.handle()
async def handle_fake_forward(bot: Bot, event: GroupMessageEvent, msg: Message = CommandArg()):
  args = str(msg).split(None, 1)
  if len(args) != 2:
    await fake_forward.finish(fake_forward.__doc__)
  try:
    uid = int(args[0])
  except:
    errors, uid = await account_aliases.match_uid(bot, event, args[0])
    if errors:
      await fake_forward.finish("\n".join(errors))
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
