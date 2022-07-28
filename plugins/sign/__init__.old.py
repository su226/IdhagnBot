import asyncio
import html
import random
from argparse import Namespace
from calendar import Calendar
from datetime import date, datetime
from io import BytesIO
from typing import Any

from aiohttp import ClientSession
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field

from util import account_aliases, command, context, currency, helper, text
from util.config import BaseConfig, BaseState


class Config(BaseConfig):
  __file__ = "sign"
  coin: int | tuple[int, int] = (80, 120)
  combo_each: float = 0.1
  combo_max: float = 1.0
  first_award: list[int] = Field(default_factory=lambda: [0.5, 0.25, 0.1])
  first_prefix: list[str] = Field(default_factory=lambda: ["🥇", "🥈", "🥉"])
  max_rank: int = 10

  @property
  def min_coin(self):
    if isinstance(self.coin, int):
      return self.coin
    return self.coin[0]

  @property
  def max_coin(self):
    if isinstance(self.coin, int):
      return self.coin
    return self.coin[1]


class UserData(BaseModel):
  combo_days: int = 0
  total_days: int = 0
  calendar: set[int] = Field(default_factory=set)
  time: datetime = datetime.min


class GroupData(BaseModel):
  users: dict[int, UserData] = Field(default_factory=dict)
  rank: list[int] = Field(default_factory=list)
  time: datetime = datetime.min


class State(BaseState):
  __file__ = "sign"
  groups: dict[int, GroupData] = Field(default_factory=dict)


CONFIG = Config.load()
STATE = State.load()
MONTHS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]


def get_or_create_group_data(gid: int) -> GroupData:
  if gid in STATE.groups:
    group_data = STATE.groups[gid]
    if group_data.time.date() != date.today():
      group_data.rank = []
  else:
    group_data = STATE.groups[gid] = GroupData()
  group_data.time = datetime.now()
  return group_data


def get_or_create_group_and_user_data(gid: int, uid: int) -> tuple[GroupData, UserData]:
  group_data = get_or_create_group_data(gid)
  if uid not in group_data.users:
    group_data.users[uid] = UserData()
  user_data = group_data.users[uid]
  sign_date = user_data.time.date()
  today = date.today()
  if sign_date.year != today.year or sign_date.month != today.month:
    user_data.calendar.clear()
  return group_data, user_data


async def make_calendar(bot: Bot, gid: int, uid: int) -> MessageSegment:
  async def get_user_infos(users: list[int]) -> dict[int, dict[str, Any]]:
    coros = [bot.get_group_member_info(group_id=gid, user_id=user) for user in users]
    return dict(zip(users, await asyncio.gather(*coros)))

  # 排行
  group_data = STATE.groups[gid]
  infos = await get_user_infos(group_data.rank)
  segments = ["<big>今日排名</big>"]
  for i, user in enumerate(group_data.rank):
    name = infos[user]["card"] or infos[user]["nickname"]
    if i < len(CONFIG.first_prefix):
      prefix = CONFIG.first_prefix[i]
    else:
      prefix = f"{i + 1}. "
    name = html.escape(name)
    if user == uid:
      name = f"<b>{name}</b>"
    time = group_data.users[user].time.strftime("%H:%M:%S")
    segments.append(f"{prefix}{name} - {time}")
  rank_im = text.render("\n".join(segments), "sans", 32, markup=True)

  today = date.today()
  weeks = Calendar().monthdayscalendar(today.year, today.month)
  im = Image.new(
    "RGB", (656 + rank_im.width, max(264 + len(weeks) * 80, rank_im.height + 64)), (255, 255, 255))
  im.paste(rank_im, (624, 32), rank_im)

  # 头像
  async with ClientSession() as http:
    response = await http.get(f"https://q1.qlogo.cn/g?b=qq&nk={uid}&s=0")
    avatar = Image.open(BytesIO(await response.read())).convert("RGB")
  mask = Image.new("L", avatar.size, 0)
  ImageDraw.Draw(mask).ellipse((0, 0, mask.width - 1, mask.height - 1), 255)
  avatar.putalpha(mask)
  avatar = avatar.resize((96, 96), Image.ANTIALIAS)
  im.paste(avatar, (32, 32), avatar)

  # 用户名
  text.paste(
    im, (152, 32), infos[uid]["card"] or infos[uid]["nickname"], "sans", 32,
    box=336, mode=text.ELLIPSIZE_END)

  # 群名
  text.paste(
    im, (152, 80), (await bot.get_group_info(group_id=gid))["group_name"], "sans", 28,
    color=(143, 143, 143))

  # 月份
  text.paste(
    im, (584, 32), MONTHS[today.month - 1] + "月", "sans", 38, color=(0, 0, 0), anchor="rt")

  # 日历头
  for x, weekday in enumerate(WEEKDAYS):
    text.paste(
      im, (32 + x * 80 + 40, 152 + 40), weekday, "sans", 28, color=(143, 143, 143), anchor="mm")

  # 日历
  user_data = group_data.users[uid]
  circle = Image.new("RGBA", (144, 144))
  ImageDraw.Draw(circle).ellipse((0, 0, 143, 143), (76, 175, 80))
  circle = circle.resize((72, 72), Image.ANTIALIAS)
  for y, days in enumerate(weeks):
    for x, day in enumerate(days):
      if day == 0:
        continue
      elif day in user_data.calendar:
        im.paste(circle, (32 + x * 80 + 4, 232 + y * 80 + 4), circle)
        color = (255, 255, 255)
      else:
        color = (0, 0, 0)
      text.paste(
        im, (32 + x * 80 + 40, 232 + y * 80 + 40), str(day), "sans", 28, color=color, anchor="mm")

  f = BytesIO()
  im.save(f, "png")
  return MessageSegment.image(f)

sign = (
  command.CommandBuilder("sign.sign", "签到", "sign")
  .in_group()
  .brief("每日签到获取金币")
  .usage(f'''\
每天签到可获得{CONFIG.min_coin}至{CONFIG.max_coin}金币
连续签到或前{len(CONFIG.first_award)}名可获得更多金币''')
  .build())


@sign.handle()
async def handle_sign(bot: Bot, event: MessageEvent):
  ctx = context.get_event_context(event)
  group_data, user_data = get_or_create_group_and_user_data(ctx, event.user_id)
  now = datetime.now()
  today = date.today()
  days = (today - user_data.time.date()).days
  if days == 0:
    await sign.finish(
      f"今天你已经签到过了\n你目前有{currency.get_coin(ctx, event.user_id)}个金币"
      + await make_calendar(bot, ctx, event.user_id))
  add_coin = random.randint(CONFIG.min_coin, CONFIG.max_coin)
  if days == 1:
    user_data.combo_days += 1
  else:
    user_data.combo_days = 0
  segments = [""]
  if user_data.combo_days > 0:
    combo = min(CONFIG.combo_each * user_data.combo_days, CONFIG.combo_max)
    add_coin *= 1 + combo
    segments.append(f"连签加成：{round(combo * 100)}%")
  cur_rank = len(group_data.rank)
  if cur_rank < len(CONFIG.first_award):
    award = CONFIG.first_award[cur_rank]
    add_coin *= 1 + award
    segments.append(f"排名加成：{round(award * 100)}%")
  user_data.time = now
  user_data.total_days += 1
  user_data.calendar.add(today.day)
  group_data.rank.append(event.user_id)
  add_coin = round(add_coin)
  currency.add_coin(ctx, event.user_id, add_coin)
  STATE.dump()
  segments[0] = f"签到成功，获得{add_coin}个金币，共有{currency.get_coin(ctx, event.user_id)}个金币"
  segments.append(
    f"今日排名第{cur_rank + 1}，连续签到{user_data.combo_days + 1}天，"
    f"总计签到{user_data.total_days}天")
  await sign.finish("\n".join(segments) + await make_calendar(bot, ctx, event.user_id))


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
    for i in users:
      currency.set_coin(ctx, i, 0)
      _, user_data = get_or_create_group_and_user_data(ctx, i)
      user_data.time = datetime.min
    STATE.dump()
    msg = f"已重置 {len(users)} 个用户的金币和连签加成"
  await gold.finish(msg)
