import asyncio
from typing import Dict, List, Set, Tuple, cast

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from util import command, context, misc, user_aliases

fake_forward = (
  command.CommandBuilder("fake_forward", "我有一个朋友", "朋友", "吾有一友", "friend")
  .brief("鲁迅：我没有说过这句话")
  .usage("/我有一个朋友 <用户> <消息> [-- <用户> <消息>...]")
  .build()
)
@fake_forward.handle()
async def handle_fake_forward(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
  async def match(name: str) -> None:
    uid = await user_aliases.match_uid(bot, event, name)
    match_to_uid[name] = uid
    uids.add(uid)

  messages: List[Tuple[str, str]] = []
  match_tasks: List[asyncio.Task[None]] = []
  match_to_uid: Dict[str, int] = {}
  uids: Set[int] = set()
  is_superuser = await SUPERUSER(bot, event)
  if not is_superuser:
    uids.add(event.self_id)
  for x in str(msg).split("--"):
    message = x.split(None, 1)
    if len(message) != 2:
      await fake_forward.finish(fake_forward.__doc__)
    match_tasks.append(asyncio.create_task(match(message[0])))
    messages.append(cast(Tuple[str, str], tuple(message)))
  if not messages:
    await fake_forward.finish(fake_forward.__doc__)
  errors: List[str] = []
  for i in (await asyncio.wait(match_tasks))[0]:
    if (e := i.exception()):
      errors.extend(cast(misc.AggregateError, e))
  if errors:
    await fake_forward.finish("\n".join(errors))

  async def fetch_name(uid: int) -> None:
    uid_to_name[uid] = await context.get_card_or_name(bot, event, uid)

  uid_to_name: Dict[int, str] = {}
  await asyncio.gather(*[fetch_name(uid) for uid in uids])

  nodes: List[MessageSegment] = []
  if not is_superuser:
    nodes.append(misc.forward_node(
      event.self_id, uid_to_name[event.self_id],
      "免责声明：本消息由机器人发送，仅供娱乐，切勿当真！",
    ))
  nodes.extend(
    misc.forward_node(match_to_uid[match], uid_to_name[match_to_uid[match]], content)
    for match, content in messages
  )

  await misc.send_forward_msg(bot, event, *nodes)
