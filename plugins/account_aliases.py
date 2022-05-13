import itertools
from nonebot.adapters import Bot, Event, Message
from nonebot.params import CommandArg
from util import account_aliases
import nonebot

CONFIG = account_aliases.CONFIG

def parse_boolean(value: str) -> bool:
  if value in ("true", "t", "1", "yes", "y", "on"):
    return True
  if value in ("false", "f", "0", "no", "n", "off"):
    return False
  raise ValueError("Not a vaild truthy or falsy")

match = nonebot.on_command("匹配", aliases={"match"})
match.__cmd__ = ["匹配", "match"]
match.__brief__ = "从名字匹配群成员"
match.__doc__ = '''\
/匹配 <QQ号> - 显示成员的所有名字
/匹配 <昵称、群名片或别名> - 查找名字对应的成员
只接受中文、英文和数字
不能有空格，不区分大小写
特殊符号、emoji等会被忽略'''
@match.handle()
async def handle_match(bot: Bot, event: Event, args: Message = CommandArg()):
  name = args.extract_plain_text().rstrip()
  try:
    uid = int(name)
  except ValueError:
    pass
  else:
    names = []
    groups = []
    aliases = await account_aliases.get_aliases(bot, event)
    for alias in aliases.values():
      if uid not in alias.users:
        continue
      if len(alias.users) == 1:
        names.extend(alias.names)
      else:
        groups.append("、".join(alias.names) + f"（{len(alias.users)} 个成员）")
    names = "、".join(names) if names else "（无）"
    groups = "\n".join(groups) if groups else "（无）"
    await match.finish(f"只指代 {uid} 的所有名字：\n{names}\n指代 {uid} 和其他成员的所有名字：\n{groups}")
  if " " in args:
    await match.send("不能有空格")
    return
  pattern = account_aliases.to_identifier(name)
  if not pattern:
    await match.send("有效名字为空，运行 /帮助 匹配 查看详情")
    return
  exact, inexact = await account_aliases.match(bot, event, pattern)
  values = itertools.chain(exact.values(), inexact.values())
  count = len(exact) + len(inexact)
  limit = 10
  segments = []
  if count == 0:
    segments.append(f"找不到 {pattern}")
  else:
    segments.append(f"{pattern} 可以指：")
  for _, i in zip(range(limit), values):
    segments.append(f"{i}（{'、'.join(map(str, i.patterns))}）")
  if count > limit:
    segments.append(f"等 {count} 个成员或别名")
  await match.send("\n".join(segments))
