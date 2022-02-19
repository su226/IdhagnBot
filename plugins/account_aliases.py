from nonebot.adapters import Bot, Event, Message
from nonebot.params import CommandArg
from util import context, account_aliases
import nonebot

CONFIG = account_aliases.CONFIG
STATE = account_aliases.STATE

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
/匹配 <昵称、群名片或别名>
只接受中文、英文和数字
不能有空格，不区分大小写
特殊符号、emoji等会被忽略'''
@match.handle()
async def handle_match(bot: Bot, event: Event, args: Message = CommandArg()):
  name = str(args).rstrip()
  if " " in args:
    await match.send("不能有空格")
    return
  pattern = account_aliases.to_identifier(name)
  if not pattern:
    await match.send("有效名字为空，运行 /帮助 匹配 查看详情")
    return
  aliases = await account_aliases.get_aliases(bot, event)
  all, _, _ = account_aliases.match(aliases, pattern)
  limit = 10
  segments = []
  if len(all) == 0:
    segments.append(f"找不到 {pattern}")
  else:
    segments.append(f"{pattern} 可以指：")
  if len(all) > limit:
    for _, i in zip(range(limit - 1), all.values()):
      segments.append(f"{i}（{'、'.join(map(str, i.items))}）")
    segments.append(f"等 {len(all)} 个成员或别名")
  else:
    for i in all.values():
      segments.append(f"{i}（{'、'.join(map(str, i.items))}）")
  await match.send("\n".join(segments))

trap = nonebot.on_command("trap", permission=context.Permission.SUPER)
trap.__cmd__ = "trap"
trap.__brief__ = "开启或关闭 trap"
trap.__doc__ = '''\
/trap - 列出所有trap
/trap <id> - 查看该trap是否开启
/trap <id> true|false - 开启或关闭trap'''
trap.__perm__ = context.Permission.SUPER
@trap.handle()
async def handle_trapcmd(msg = CommandArg()):
  args = str(msg).lower().split()
  if len(args) == 2:
    id, enabled = args
    if id not in CONFIG.traps:
      await trap.send(f"id 为 {id} 的 trap 不存在")
      return
    try:
      enabled = parse_boolean(enabled)
    except:
      await trap.send("/trap <id> true|false - 开启或关闭trap")
      return
    STATE.traps_enabled[id] = enabled
    STATE.dump()
    state_str = "启用" if enabled else "禁用"
    await trap.send(f"已{state_str} id 为 {id} 的 trap")
  elif len(args) == 1:
    id = args[0]
    if id not in CONFIG.traps:
      await trap.send(f"id 为 {id} 的 trap 不存在")
      return
    state_str = "启用" if STATE.traps_enabled.get(id, False) else "禁用"
    await trap.send(f"id 为 {id} 的 trap 已{state_str}")
  else:
    traps = "\n".join(map(lambda x: f"{'✓' if STATE.traps_enabled.get(x[0], False) else '✗'} {x[0]}: {x[1].reason}", CONFIG.traps.items()))
    await trap.send("trap 列表：\n" + traps)
