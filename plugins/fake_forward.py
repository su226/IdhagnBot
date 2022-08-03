import asyncio
from typing import Awaitable, cast

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg

from util import account_aliases, command, util


async def get_name_or_card(bot: Bot, event: MessageEvent, uid: int, gid: int) -> str:
  try:
    if gid == -1:
      raise RuntimeError
    info = await bot.get_group_member_info(group_id=gid, user_id=uid)
    return info["card"] or info["nickname"]
  except (RuntimeError, ActionFailed):
    return (await bot.get_stranger_info(user_id=uid))["nickname"]


USAGE = "/我有一个朋友 <用户> <消息> [-- <用户> <消息>...]"
fake_forward = (
  command.CommandBuilder("fake_forward", "我有一个朋友", "朋友", "吾有一友", "friend")
  .brief("鲁迅：我没有说过这句话")
  .usage(USAGE)
  .private(False)
  .build())


@fake_forward.handle()
async def handle_fake_forward(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
  async def match(name: str) -> None:
    uid = await account_aliases.match_uid(bot, event, name)
    match_to_uid[name] = uid
    uids.add(uid)

  messages: list[tuple[str, str]] = []
  match_coros: list[Awaitable[None]] = []
  match_to_uid: dict[str, int] = {}
  uids: set[int] = {event.self_id}
  for x in str(msg).split("--"):
    message = x.split(None, 1)
    if len(message) != 2:
      await fake_forward.finish(USAGE)
    match_coros.append(match(message[0]))
    messages.append(tuple(message))
  if not messages:
    await fake_forward.finish(USAGE)
  done, _ = await asyncio.wait(match_coros)
  errors = []
  for i in done:
    if (e := i.exception()):
      errors.extend(cast(util.AggregateError, e))
  if errors:
    await fake_forward.finish("\n".join(errors))

  async def fetch_name(uid: int) -> None:
    uid_to_name[uid] = await get_name_or_card(bot, event, uid, gid)

  uid_to_name: dict[int, str] = {}
  gid = event.group_id if isinstance(event, GroupMessageEvent) else -1
  await asyncio.gather(*[fetch_name(uid) for uid in uids])

  nodes = [
    {
      "type": "node",
      "data": {
        "name": uid_to_name[event.self_id],
        "uin": event.self_id,
        "content": "免责声明：本消息由机器人发送，仅供娱乐，切勿当真！"
      }
    }, *({
      "type": "node",
      "data": {
        "name": uid_to_name[match_to_uid[match]],
        "uin": match_to_uid[match],
        "content": content
      }
    } for match, content in messages)
  ]
  if isinstance(event, GroupMessageEvent):
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=nodes)
  else:
    await bot.call_api("send_private_forward_msg", user_id=event.user_id, messages=nodes)
