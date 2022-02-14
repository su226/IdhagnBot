from util.config import BaseModel, BaseConfig, BaseState, Field
from core_plugins.context.typing import Context
from dataclasses import dataclass
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.params import CommandArg
import nonebot
import re

context: Context = nonebot.require("context")
exports = nonebot.export()

class Trap(BaseModel):
  reason: str = "无原因"
  users: list[int]

class Alias(BaseModel):
  names: list[str]
  users: tuple[int, ...]

class Aliases(BaseModel):
  contexts: list[int] = Field(default_factory=list)
  aliases: list[Alias]

class Config(BaseConfig):
  __file__ = "account_aliases"
  traps: dict[str, Trap] = Field(default_factory=dict)
  aliases: list[Aliases] = Field(default_factory=list)

class State(BaseState):
  __file__ = "account_aliases"
  traps_enabled: dict[str, bool] = Field(default_factory=dict)

@dataclass
class MatchPattern:
  name: str
  exact: bool
  def __str__(self) -> str:
    return f"*{self.name}" if self.exact else self.name

@dataclass
class Match:
  uids: tuple[int, ...]
  items: list[MatchPattern]
  def __str__(self) -> str:
    if len(self.uids) > 1:
      return f"{self.uids[0]} 等 {len(self.uids)} 个成员"
    return str(self.uids[0])

@exports
class MatchException(Exception):
  def __init__(self, errors: list[str]) -> None:
    super().__init__("这个异常没有被正确捕获")
    self.errors = errors

config = Config.load()
state = State.load()

CHINESE_RE = re.compile(r"[a-zA-Z0-9\u4e00-\u9fa5]+")
@exports
def to_identifier(data: str) -> str:
  return "".join(CHINESE_RE.findall(data)).lower()

@exports
async def get_aliases(bot: Bot, event: Event) -> dict[int, Alias]:
  ctx = context.get_context(event)
  aliases: dict[int, Alias] = {}
  for i in config.aliases:
    if not context.in_context(ctx, *i.contexts):
      continue
    for alias in i.aliases:
      key = hash(alias.users)
      if key not in aliases:
        aliases[key] = Alias(names=[], users=alias.users)
      aliases[key].names.extend(alias.names)
  if ctx == context.PRIVATE:
    return aliases
  for user in await bot.get_group_member_list(group_id=ctx):
    users = (user["user_id"],)
    key = hash(users)
    if key not in aliases:
      aliases[key] = Alias(names=[], users=users)
    aliases[key].names.extend(filter(len, {
      to_identifier(user["nickname"]),
      to_identifier(user["card"])
    }))
  return aliases

@exports
def match(aliases: dict[int, Alias], pattern: str) -> tuple[dict[int, Match], dict[int, Match], dict[int, Match]]:
  all: dict[int, Match] = {}
  exact: dict[int, Match] = {}
  inexact: dict[int, Match] = {}
  def get(matches: dict[int, Match], id: int, alias: Alias) -> Match:
    if id not in matches:
      matches[id] = Match(alias.users, [])
    return matches[id]
  for id, alias in aliases.items():
    for name in alias.names:
      if pattern == name:
        matched = MatchPattern(name, True)
        get(exact, id, alias).items.append(matched)
        get(all, id, alias).items.append(matched)
      elif pattern in name:
        matched = MatchPattern(name, False)
        get(inexact, id, alias).items.append(matched)
        get(all, id, alias).items.append(matched)
  return all, exact, inexact

AMBIGUOUS_LIMIT = 5

@exports
def try_match(aliases: dict[int, Alias], pattern: str, multiple: bool = False, trap: bool = False) -> int | list[int]:
  pattern = to_identifier(pattern)
  all, exact, inexact = match(aliases, pattern)
  matches = list((inexact if len(exact) == 0 else exact).values())
  if len(matches) > 1:
    count = len(exact) + len(inexact)
    segments = [f"{pattern} 具有歧义，可以指："]
    if count > AMBIGUOUS_LIMIT:
      for _, i in zip(range(AMBIGUOUS_LIMIT - 1), all.values()):
        segments.append(f"{i}（{'、'.join(map(str, i.items))}）")
      segments.append(f"等 {count} 个成员或别名")
    else:
      for i in all.values():
        segments.append(f"{i}（{'、'.join(map(str, i.items))}）")
    raise MatchException(["\n".join(segments)])
  elif len(matches) == 0:
    raise MatchException([f"找不到 {pattern}"])
  errors = []
  if not multiple and len(matches[0].uids) > 1:
    comment = " "
    if len(matches[0].items) > 1:
      comment = "（" + "、".join(map(str, match.items[1:])) + "）"
    errors.append(f"{matches[0].items[0]}{comment}包含多个成员")
  if trap:
    for user in matches[0].uids:
      for id, t in config.traps.items():
        if state.traps_enabled.get(id, False) and user in t.users:
          errors.append(f"发现包含 {user} 的 trap，理由为 {t.reason}")
          break
  if len(errors):
    raise MatchException(errors)
  if multiple:
    return matches[0].uids
  else:
    return matches[0].uids[0]

def parse_boolean(value: str) -> bool:
  if value in ("true", "t", "1", "yes", "y", "on"):
    return True
  if value in ("false", "f", "0", "no", "n", "off"):
    return False
  raise ValueError("Not a vaild truthy or falsy")

trap = nonebot.on_command("trap", permission=context.SUPER)
trap.__cmd__ = "trap"
trap.__brief__ = "开启或关闭 trap"
trap.__doc__ = '''\
/trap - 列出所有trap
/trap <id> - 查看该trap是否开启
/trap <id> true|false - 开启或关闭trap'''
trap.__perm__ = context.SUPER
@trap.handle()
async def handle_trapcmd(msg = CommandArg()):
  args = str(msg).lower().split()
  if len(args) == 2:
    id, enabled = args
    if id not in config.traps:
      await trap.send(f"id 为 {id} 的 trap 不存在")
      return
    try:
      enabled = parse_boolean(enabled)
    except:
      await trap.send("/trap <id> true|false - 开启或关闭trap")
      return
    state.traps_enabled[id] = enabled
    state.dump()
    state_str = "启用" if enabled else "禁用"
    await trap.send(f"已{state_str} id 为 {id} 的 trap")
  elif len(args) == 1:
    id = args[0]
    if id not in config.traps:
      await trap.send(f"id 为 {id} 的 trap 不存在")
      return
    state_str = "启用" if state.traps_enabled.get(id, False) else "禁用"
    await trap.send(f"id 为 {id} 的 trap 已{state_str}")
  else:
    traps = "\n".join(map(lambda x: f"{'✓' if state.traps_enabled.get(x[0], False) else '✗'} {x[0]}: {x[1].reason}", config.traps.items()))
    await trap.send("trap 列表：\n" + traps)
