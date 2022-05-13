from dataclasses import dataclass
from typing import Callable, Literal, overload
import itertools
import re
import time

from pydantic import BaseModel, Field
from nonebot.adapters.onebot.v11 import Bot, Event

from util.config import BaseConfig
from util import context

class Alias(BaseModel):
  names: list[str]
  users: tuple[int, ...]

class Aliases(BaseModel):
  contexts: list[int] = Field(default_factory=list)
  aliases: list[Alias]

class Config(BaseConfig, file="account_aliases"):
  aliases: list[Aliases] = Field(default_factory=list)

@dataclass
class MatchPattern:
  name: str
  exact: bool
  def __str__(self) -> str:
    return f"*{self.name}" if self.exact else self.name

@dataclass
class Match:
  uids: tuple[int, ...]
  patterns: list[MatchPattern]
  def __str__(self) -> str:
    if len(self.uids) > 1:
      return f"{self.uids[0]} 等 {len(self.uids)} 个成员"
    return str(self.uids[0])

AliasesDict = dict[int, Alias]
CACHE: dict[int, tuple[float, AliasesDict]] = {}

@Config.reloadable
def reload_config(config: Config):
  CACHE.clear()
  global CONFIG
  CONFIG = config

IDENTIFIER_RE = re.compile(r"[a-zA-Z0-9\u4e00-\u9fa5]+")
def to_identifier(data: str) -> str:
  return "".join(IDENTIFIER_RE.findall(data)).lower()

async def get_aliases(bot: Bot, event: Event) -> AliasesDict:
  ctx = context.get_event_context(event)
  curtime = time.time()
  cachetime, aliases = CACHE.get(ctx, (0.0, {}))
  if cachetime > curtime - 600:
    return aliases
  aliases: AliasesDict = {}
  CACHE[ctx] = (curtime, aliases)
  for i in CONFIG.aliases:
    if not context.in_group(ctx, *i.contexts):
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

async def match(bot: Bot, event: Event, pattern: str) -> tuple[dict[int, Match], dict[int, Match]]:
  exact: dict[int, Match] = {}
  inexact: dict[int, Match] = {}
  def get(matches: dict[int, Match], id: int, alias: Alias) -> Match:
    if id not in matches:
      matches[id] = Match(alias.users, [])
    return matches[id]
  for id, alias in (await get_aliases(bot, event)).items():
    for name in alias.names:
      if pattern == name:
        matched = MatchPattern(name, True)
        get(exact, id, alias).patterns.append(matched)
      elif pattern in name:
        matched = MatchPattern(name, False)
        get(inexact, id, alias).patterns.append(matched)
  return exact, inexact

AMBIGUOUS_LIMIT = 5

@overload
async def match_uid(bot: Bot, event: Event, raw_pattern: str, multiple: Literal[False] = False) -> tuple[list[str], int]: ...
@overload
async def match_uid(bot: Bot, event: Event, raw_pattern: str, multiple: Literal[True] = True) -> tuple[list[str], list[int]]: ...
async def match_uid(bot: Bot, event: Event, raw_pattern: str, multiple: bool = False) -> tuple[list[str], int | list[int]]:
  pattern = to_identifier(raw_pattern)
  default = [] if multiple else -1
  if not pattern:
    return [f"有效名字为空：{raw_pattern}"], default
  exact, inexact = await match(bot, event, pattern)
  matches = list((inexact if len(exact) == 0 else exact).values())
  if len(matches) > 1:
    count = len(exact) + len(inexact)
    segments = [f"{pattern} 具有歧义，可以指："]
    values = itertools.chain(exact.values(), inexact.values())
    for _, i in zip(range(AMBIGUOUS_LIMIT), values):
      segments.append(f"{i}（{'、'.join(map(str, i.patterns))}）")
    if count > AMBIGUOUS_LIMIT:
      segments.append(f"等 {count} 个成员或别名")
    return ["\n".join(segments)], default
  elif len(matches) == 0:
    return [f"找不到 {pattern}"], default
  errors = []
  if not multiple and len(matches[0].uids) > 1:
    comment = " "
    if len(matches[0].patterns) > 1:
      comment = "（" + "、".join(map(str, matches[0].patterns[1:])) + "）"
    errors.append(f"{matches[0].patterns[0]}{comment}包含多个成员")
  if multiple:
    return errors, list(matches[0].uids)
  else:
    return errors, matches[0].uids[0]
