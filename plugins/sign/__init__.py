import asyncio
import random
from argparse import Namespace
from datetime import date, datetime

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser

from util import account_aliases, command, context, currency, help, helper

from . import leaderboard
from .config import CONFIG, STATE, Config, FormatData
from .formatters.legacy import format as formatter_legacy
from .formatters.ring import format as formatter_ring


FORMATTERS = {
  "legacy": formatter_legacy,
  "ring": formatter_ring,
}


sign = (
  command.CommandBuilder("sign.sign", "签到", "sign")
  .in_group()
  .brief("每日签到获取金币")
  .build())


@CONFIG.onload()
def onload(_: Config | None, cur: Config):
  item = help.CommandItem.find("签到")
  item.raw_usage = f'''\
每天签到可获得{cur.min_coin}至{cur.max_coin}金币
连续签到或前{len(cur.first_award)}名可获得更多金币'''


@sign.handle()
async def handle_sign(bot: Bot, event: MessageEvent):
  uid = event.user_id
  gid = context.get_event_context(event)
  config = CONFIG()
  formatter = FORMATTERS[config.formatter]
  group_data = STATE(gid)
  group_data.update()
  user_data = group_data.get_user(uid)
  format_data = FormatData(uid, gid, -1, -1, None, None)

  now = datetime.now()
  days = (now.date() - user_data.time.date()).days
  if days == 0:
    await sign.finish(await formatter(bot, format_data))

  coin = random.randint(config.min_coin, config.max_coin)
  format_data.original_coin = coin

  if days == 1:
    user_data.combo_days += 1
  else:
    user_data.combo_days = 0
  if user_data.combo_days > 0:
    combo_bonus = min(config.combo_each * user_data.combo_days, config.combo_max)
    coin *= 1 + combo_bonus
    format_data.combo_bonus = combo_bonus

  rank = len(group_data.rank)
  if rank < len(config.first_award):
    rank_bonus = config.first_award[rank]
    coin *= 1 + rank_bonus
    format_data.rank_bonus = rank_bonus

  user_data.time = now
  user_data.total_days += 1
  user_data.calendar.add(now.day)
  group_data.rank.append(uid)
  coin = round(coin)
  format_data.coin = coin
  currency.add_coin(gid, uid, coin)
  STATE.dump(gid)

  await sign.finish(await formatter(bot, format_data))


async def match_all(bot: Bot, event: MessageEvent, patterns: list[str]) -> set[int]:
  async def do_match(pattern: str) -> tuple[int]:
    if pattern in ("全部", "全体", "all"):
      ctx = context.get_event_context(event)
      return tuple(i["user_id"] for i in await bot.get_group_member_list(group_id=ctx))
    return await account_aliases.match_uid(bot, event, pattern, True)
  coros = [do_match(i) for i in patterns]
  errors: list[helper.AggregateError] = []
  users = set()
  for i in await asyncio.gather(*coros, return_exceptions=True):
    if isinstance(i, helper.AggregateError):
      errors.append(i)
    else:
      users.update(i)
  if errors:
    raise helper.AggregateError(*errors)
  return users

gold_parser = ArgumentParser("/金币", add_help=False)
gold_parser.add_argument(
  "users", nargs="+", metavar="用户",
  help="可使用昵称、群名片或QQ号，可指定多个，也可使用\"全部\"指代全体成员")
group = gold_parser.add_mutually_exclusive_group(required=True)
group.add_argument(
  "-add", "-增加", type=int, metavar="数量",
  help="增加指定成员的金币数量，负数为减少金币（但不会减少至低于0个）")
group.add_argument(
  "-set", "-设置", type=int, metavar="数量",
  help="设置指定成员的金币数量（-set 0 不会重置连签加成或签到日历）")
group.add_argument(
  "-reset", "-重置", action="store_true", help="清空金币并重置连签加成（不会重置签到日历）")


gold = (
  command.CommandBuilder("sign.gold", "金币", "gold")
  .in_group()
  .level("admin")
  .brief("管理群员的金币")
  .shell(gold_parser)
  .build())


@gold.handle()
async def handle_gold(
  bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()
) -> None:
  if isinstance(args, ParserExit):
    await gold.finish(args.message)
  try:
    users = await match_all(bot, event, args.users)
  except helper.AggregateError as e:
    await gold.finish("\n".join(e))
  ctx = context.get_event_context(event)
  if args.add is not None:
    for i in users:
      currency.add_coin(ctx, i, args.add)
    if args.add < 0:
      msg = f"已为 {len(users)} 个用户减少 {-args.add} 个金币"
    else:
      msg = f"已为 {len(users)} 个用户增加 {args.add} 个金币"
  elif args.set is not None:
    for i in users:
      currency.set_coin(ctx, i, args.set)
    msg = f"已设置 {len(users)} 个用户的金币为 {args.set}"
  else:
    state = STATE(ctx)
    for i in users:
      currency.set_coin(ctx, i, 0)
      user_data = state.get_user(i)
      user_data.time = datetime.min
    STATE.dump(ctx)
    msg = f"已重置 {len(users)} 个用户的金币和连签加成"
  await gold.finish(msg)
