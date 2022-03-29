from aiohttp import ClientSession
from calendar import Calendar
from datetime import date, datetime, time, timedelta
from io import BytesIO
from PIL import Image, ImageDraw
from util import context, currency, resources
from util.config import BaseConfig, BaseModel, BaseState, Field
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
import nonebot
import random

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
    response = await http.get(f"https://q1.qlogo.cn/g?b=qq&nk={uid}&s=640")
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
  large_font = resources.font("sans", 32)
  font = resources.font("sans", 28)
  info = await bot.get_group_member_info(group_id=gid, user_id=uid)
  draw.text((152, 32), info["card"] or info["nickname"], (0, 0, 0), large_font)
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

def format_delta(d: timedelta) -> str:
  seconds = d.seconds
  minutes, seconds = divmod(seconds, 60)
  hours,   minutes = divmod(minutes, 60)
  segments = []
  if hours != 0:
    segments.append(f"{hours}时")
  if minutes != 0:
    segments.append(f"{minutes}分")
  if seconds != 0 or not segments:
    segments.append(f"{seconds}秒")
  return "".join(segments)

sign = nonebot.on_command("签到", context.in_context_rule(context.ANY_GROUP), {"sign"})
sign.__cmd__ = ["签到", "sign"]
sign.__brief__ = "每日签到获取金币"
sign.__doc__ = f'''\
每天签到可获得{CONFIG.min_coin}至{CONFIG.max_coin}金币
签到每日{CONFIG.reset_time.strftime("%H:%M:%S")}重置
连续签到或前{len(CONFIG.first_award)}名可获得更多金币
两次签到须间隔至少{format_delta(CONFIG.cooldown)}'''
@sign.handle()
async def handle_sign(bot: Bot, event: MessageEvent):
  ctx = context.get_event_context(event)
  group_data, user_data = get_group_and_user_data(ctx, event.user_id)
  now = datetime.now()
  today = get_today()
  days = (today - get_date(user_data.time)).days
  if days == 0:
    await sign.finish("今天你已经签到过了")
  elif (remaining := CONFIG.cooldown - (now - user_data.time)) > timedelta():
    await sign.finish(f"签到还在冷却中，剩余{format_delta(remaining)}")
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
  await sign.finish(Message("\n".join(segments)) + MessageSegment.image(await make_calendar(bot, ctx, event.user_id)))

signcal = nonebot.on_command("签到日历", context.in_context_rule(context.ANY_GROUP), {"signcal"})
signcal.__cmd__ = ["签到日历", "signcal"]
signcal.__brief__ = "查看本月的签到天数"
@signcal.handle()
async def handle_signcal(bot: Bot, event: MessageEvent):
  ctx = context.get_event_context(event)
  get_group_and_user_data(ctx, event.user_id)
  await signcal.finish(MessageSegment.image(await make_calendar(bot, ctx, event.user_id)))

signrank = nonebot.on_command("签到排行", context.in_context_rule(context.ANY_GROUP), {"signrank"})
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
  await signcal.finish("\n".join(segments))

coins = nonebot.on_command("金币", context.in_context_rule(context.ANY_GROUP), {"gold"})
coins.__cmd__ = ["金币", "gold"]
coins.__brief__ = "查看金币数量"
@coins.handle()
async def handle_coins(event: MessageEvent):
  await coins.finish(f"你目前有{currency.get_coin(context.get_event_context(event), event.user_id)}个金币")
