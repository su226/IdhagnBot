from argparse import Namespace
from calendar import Calendar
from datetime import date, datetime, time, timedelta
from io import BytesIO
import asyncio
import random

from aiohttp import ClientSession
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot.params import ShellCommandArgs
import nonebot

from util import context, currency, resources, account_aliases, text, helper
from util.config import BaseConfig, BaseState

class Config(BaseConfig):
  __file__ = "sign"
  reset_time: time = time(0, 0, 0)
  cooldown: timedelta = timedelta(0)
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

def get_date(t: datetime) -> date:
  d = t.date()
  if t.time() < CONFIG.reset_time and d > datetime.min:
    d -= timedelta(1)
  return d

def get_today() -> date:
  return get_date(datetime.now())

def get_group_data(gid: int) -> GroupData:
  if gid in STATE.groups:
    group_data = STATE.groups[gid]
    if get_date(group_data.time) != get_today():
      group_data.rank = []
  else:
    group_data = STATE.groups[gid] = GroupData()
  group_data.time = datetime.now()
  return group_data

def get_group_and_user_data(gid: int, uid: int) -> tuple[GroupData, UserData]:
  group_data = get_group_data(gid)
  if uid not in group_data.users:
    group_data.users[uid] = UserData()
  user_data = group_data.users[uid]
  sign_date = get_date(user_data.time)
  today = get_today()
  if sign_date.year != today.year or sign_date.month != today.month:
    user_data.calendar.clear()
  return group_data, user_data

async def make_calendar(bot: Bot, gid: int, uid: int) -> BytesIO:
  user_data = STATE.groups[gid].users[uid]
  async with ClientSession() as http:
    response = await http.get(f"https://q1.qlogo.cn/g?b=qq&nk={uid}&s=0")
    avatar = Image.open(BytesIO(await response.read())).convert("RGB")
  mask = Image.new("L", avatar.size, 0)
  ImageDraw.Draw(mask).ellipse((0, 0, mask.width - 1, mask.height - 1), 255)
  avatar.putalpha(mask)
  avatar = avatar.resize((96, 96), Image.ANTIALIAS)
  circle = Image.new("L", (144, 144), 0)
  ImageDraw.Draw(circle).ellipse((0, 0, 143, 143), 255)
  circle = circle.resize((72, 72), Image.ANTIALIAS)
  today = get_today()
  weeks = Calendar().monthdayscalendar(today.year, today.month)
  im = Image.new("RGB", (624, 264 + len(weeks) * 80), (255, 255, 255))
  draw = ImageDraw.Draw(im)
  im.paste(avatar, (32, 32), avatar)
  x_large_font = resources.font("sans", 40)
  # large_font = resources.font("sans", 32)
  font = resources.font("sans", 28)
  info = await bot.get_group_member_info(group_id=gid, user_id=uid)
  # draw.text((152, 32), info["card"] or info["nickname"], (0, 0, 0), large_font)
  im2 = text.render(info["card"] or info["nickname"], "sans", 32, box=336, mode=text.ELLIPSIZE_END)
  im.paste(im2, (152, 32), im2)
  draw.text((152, 80), (await bot.get_group_info(group_id=gid))["group_name"], (143, 143, 143), font)
  draw.text((584, 32), ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"][today.month - 1] + "月", (0, 0, 0), x_large_font, "ra")
  for x, weekday in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
    draw.text((32 + x * 80 + 40, 152 + 40), weekday, (143, 143, 143), font, "mm")
  for y, days in enumerate(weeks):
    for x, day in enumerate(days):
      if day != 0:
        if day in user_data.calendar:
          draw.bitmap((32 + x * 80 + 4, 232 + y * 80 + 4), circle, (76, 175, 80))
          color = (255, 255, 255)
        else:
          color = (0, 0, 0)
        draw.text((32 + x * 80 + 40, 232 + y * 80 + 40), str(day), color, font, "mm")
  f = BytesIO()
  im.save(f, "png")
  return f

sign = nonebot.on_command("签到", context.in_group_rule(context.ANY_GROUP), {"sign"})
sign.__cmd__ = ["签到", "sign"]
sign.__brief__ = "每日签到获取金币"
sign.__doc__ = f'''\
每天签到可获得{CONFIG.min_coin}至{CONFIG.max_coin}金币
签到每日{CONFIG.reset_time.strftime("%H:%M:%S")}重置
连续签到或前{len(CONFIG.first_award)}名可获得更多金币
两次签到须间隔至少{helper.format_time(CONFIG.cooldown)}'''
@sign.handle()
async def handle_sign(bot: Bot, event: MessageEvent):
  ctx = context.get_event_context(event)
  group_data, user_data = get_group_and_user_data(ctx, event.user_id)
  now = datetime.now()
  today = get_today()
  days = (today - get_date(user_data.time)).days
  if days == 0:
    await sign.finish(f"今天你已经签到过了\n你目前有{currency.get_coin(ctx, event.user_id)}个金币" + MessageSegment.image(await make_calendar(bot, ctx, event.user_id)))
  elif (remaining := CONFIG.cooldown - (now - user_data.time)) > timedelta():
    await sign.finish(f"签到还在冷却中，剩余{helper.format_time(remaining)}")
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
  segments.append(f"今日排名第{cur_rank + 1}，连续签到{user_data.combo_days + 1}天，总计签到{user_data.total_days}天")
  await sign.finish("\n".join(segments) + MessageSegment.image(await make_calendar(bot, ctx, event.user_id)))

signrank = nonebot.on_command("签到排行", context.in_group_rule(context.ANY_GROUP), {"signrank"})
signrank.__cmd__ = ["签到排行", "signrank"]
signrank.__brief__ = "查看今天的签到排行"
@signrank.handle()
async def handle_signcal(bot: Bot, event: MessageEvent):
  ctx = context.get_event_context(event)
  group_data = get_group_data(ctx)
  if len(group_data.rank) == 0:
    await signrank.finish("今天还没有人签到")
  segments = [f"{get_today().strftime('%Y/%m/%d')}的签到排名："]
  for i, uid in zip(range(CONFIG.max_rank), group_data.rank):
    info = await bot.get_group_member_info(group_id=ctx, user_id=uid)
    name = info["card"] or info["nickname"]
    time_str = group_data.users[uid].time.strftime('%H:%M:%S')
    if i < len(CONFIG.first_prefix):
      prefix = CONFIG.first_prefix[i]
    else:
      prefix = f"{i + 1}:"
    segments.append(f"{prefix} {name} {time_str}")
  await signrank.finish("\n".join(segments))

async def match_all(bot: Bot, event: MessageEvent, patterns: list[str]) -> tuple[list[str], set[int]]:
  async def do_match(pattern: str) -> tuple[list[str], list[int]]:
    try:
      return [], [int(pattern)]
    except ValueError:
      pass
    if pattern in ("全部", "全体", "all"):
      ctx = context.get_event_context(event)
      return [], [i["user_id"] for i in await bot.get_group_member_list(group_id=ctx)]
    else:
      return await account_aliases.match_uid(bot, event, pattern, True)
  coros = [do_match(i) for i in patterns]
  errors, users = [], set()
  for e, u in await asyncio.gather(*coros):
    errors.extend(e)
    users.update(u)
  return errors, users

gold_parser = ArgumentParser("/金币", add_help=False)
gold_parser.add_argument("users", nargs="+", metavar="用户", help="可使用昵称、群名片或QQ号，可指定多个，也可使用\"全部\"指代全体成员")
group = gold_parser.add_mutually_exclusive_group(required=True)
group.add_argument("-add", "-增加", type=int, metavar="数量", help="增加指定成员的金币数量，负数为减少金币（但不会减少至低于0个）")
group.add_argument("-set", "-设置", type=int, metavar="数量", help="设置指定成员的金币数量（-set 0 不会重置连签加成或签到日历）")
group.add_argument("-reset", "-重置", action="store_true", help="清空金币并重置连签加成（不会重置签到日历）")
gold = nonebot.on_shell_command("金币", context.in_group_rule(context.ANY_GROUP), parser=gold_parser, permission=context.Permission.ADMIN)
gold.__cmd__ = "金币"
gold.__brief__ = "管理群员的金币"
gold.__doc__ = gold_parser.format_help()
gold.__ctx__ = [context.ANY_GROUP]
gold.__perm__ = context.Permission.ADMIN
@gold.handle()
async def handle_gold(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await gold.finish(args.message)
  errors, users = await match_all(bot, event, args.users)
  if errors:
    await gold.finish("\n".join(errors))
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
      _, user_data = get_group_and_user_data(ctx, i)
      user_data.time = datetime.min
    STATE.dump()
    msg = f"已重置 {len(users)} 个用户的金币和连签加成"
  await gold.finish(msg)
