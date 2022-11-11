import itertools

import nonebot
from nonebot.adapters.onebot.v11 import Bot, Event, Message, NoticeEvent
from nonebot.params import CommandArg

from util import command, user_aliases


async def check_invaildate(event: NoticeEvent) -> bool:
  return event.notice_type in {"group_card", "group_increase", "group_decrease"}
invaildate = nonebot.on_notice(check_invaildate)
@invaildate.handle()
async def handle_invaildate(event: NoticeEvent) -> None:
  group_id: int = getattr(event, "group_id")
  if group_id in user_aliases.CACHE:
    del user_aliases.CACHE[group_id]


async def format_aliases(bot: Bot, event: Event, uid: int) -> str:
  names = []
  groups = []
  aliases = await user_aliases.get_aliases(bot, event)
  for alias in aliases.values():
    if uid not in alias.users:
      continue
    if len(alias.users) == 1:
      names.extend(alias.names)
    else:
      groups.append("、".join(alias.names) + f"（{len(alias.users)} 个成员）")
  names = "、".join(names) if names else "（无）"
  groups = "\n".join(groups) if groups else "（无）"
  return f"只指代 {uid} 的所有名字：\n{names}\n指代 {uid} 和其他成员的所有名字：\n{groups}"


match = (
  command.CommandBuilder("account_aliases.match", "匹配", "match")
  .brief("从名字匹配群成员")
  .usage('''\
/匹配 <QQ号> - 显示成员的所有名字
/匹配 <昵称、群名片或别名> - 查找名字对应的成员
只接受中文、英文和数字
不能有空格，不区分大小写
特殊符号、emoji等会被忽略''')
  .build()
)
@match.handle()
async def handle_match(bot: Bot, event: Event, args: Message = CommandArg()):
  name = args.extract_plain_text().rstrip()
  try:
    uid = int(name)
  except ValueError:
    pass
  else:
    await match.finish(await format_aliases(bot, event, uid))
  if " " in args:
    await match.finish("不能有空格")
  pattern = user_aliases.to_identifier(name)
  if not pattern:
    await match.finish("有效名字为空，发送 /帮助 匹配 查看详情")
  exact, inexact = await user_aliases.match(bot, event, pattern)
  values = itertools.chain(exact.values(), inexact.values())
  count = len(exact) + len(inexact)
  limit = 10
  segments = []
  if count == 0:
    segments.append(f"找不到 {pattern}")
  else:
    segments.append(f"{pattern} 可以指：")
  for i, m in zip(range(limit), values):
    segments.append(f"{m}（{'、'.join(map(str, m.patterns))}）")
    if i == 0 and count == 1 and len(m.uids) == 1:
      segments.append(await format_aliases(bot, event, m.uids[0]))
  if count > limit:
    segments.append(f"等 {count} 个成员或别名")
  await match.finish("\n".join(segments))
