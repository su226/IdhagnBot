import asyncio
import math
import re
from datetime import datetime
from html.parser import HTMLParser
from io import StringIO
from typing import Any, Collection, Literal, Optional, Union

import nonebot
from nonebot.adapters.onebot.v11 import (
  Bot,
  Event,
  GroupIncreaseNoticeEvent,
  GroupRequestEvent,
  Message,
)
from nonebot.params import ArgStr, CommandArg
from nonebot.typing import T_State
from pydantic import BaseModel, Field, SecretStr, field_validator

from util import command, configs, context, misc


class Config(BaseModel):
  # 公共 API 提供的接口和数据似乎有点少
  # 从网页查询有上黑等级、上黑时间、上黑原因和登记人，但使用 API 查询只有上黑原因
  # 并且没有批量查询，没法写查询全群
  # 对不起幻梦老师了
  host: str = "https://fz.qimeng.fun"
  token: SecretStr = SecretStr("")
  check_join: misc.EnableSet = misc.EnableSet.false()
  check_request: misc.EnableSet = misc.EnableSet.false()
  reject_request: misc.EnableSet = misc.EnableSet.false()
  # 默认忽略Q群管家
  ignore: set[int] = Field(default_factory=lambda: {2854196310})

  @property
  def use_spider(self) -> bool:
    return self.token.get_secret_value() == "spider"


class SingleParser(HTMLParser):
  def __init__(self) -> None:
    super().__init__()
    self.level = 0
    self.in_script = False
    self.text = StringIO()

  def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
    if self.level:
      if tag == "script":
        self.in_script = True
      if tag != "br":
        self.level += 1
    elif ("class", "header-img") in attrs:
      self.level = 3

  def handle_data(self, data: str) -> None:
    if self.level and not self.in_script:
      self.text.write(data.strip())

  def handle_endtag(self, tag: str) -> None:
    if self.level:
      if tag in ("h4", "h5", "p"):
        self.text.write("\n")
      elif tag == "script":
        self.in_script = False
      self.level -= 1

  def getvalue(self) -> str:
    return self.text.getvalue().lstrip("◈").rstrip("\n◈")


class BatchParser(HTMLParser):
  def __init__(self) -> None:
    super().__init__()
    self.begin = False
    self.lines: list[str] = []

  def handle_data(self, data: str) -> None:
    data = data.strip()
    if data == "qiehuan('PiLiang')":
      self.begin = True
    elif data == "功能按钮":
      self.begin = False
    elif self.begin and data:
      self.lines.append(data)


class ApiBasicInfo(BaseModel):
  user: int
  tel: bool
  wx: bool
  zfb: bool
  shiming: bool


class ApiStatInfo(BaseModel):
  group_num: int
  m_send_num: int
  send_num: int
  first_send: Optional[datetime]
  last_send: Optional[datetime]

  @field_validator("first_send", "last_send", mode="before")
  @staticmethod
  def validate_date(value: Any) -> Optional[datetime]:
    if value == "":
      return None
    match = SEND_DATE_RE.match(value)
    if not match:
      raise ValueError("Invalid date")
    return datetime(
      int(match[1]),
      int(match[2]),
      int(match[3]),
      int(match[4]),
      int(match[5]),
      int(match[6]),
    )


class ApiBanInfoNone(BaseModel):
  yh: bool
  type: Literal["none"]
  note: None
  admin: None
  level: None
  date: None

  @field_validator("note", "admin", "level", "date", mode="before")
  @staticmethod
  def validate_info(value: Any) -> Any:
    if value == "":
      return None


class ApiBanInfoSome(BaseModel):
  yh: bool
  type: Literal["yunhei", "bilei"]
  note: str
  admin: str
  level: int
  date: datetime


class ApiResult(BaseModel):
  info: tuple[ApiBasicInfo, ApiStatInfo, Union[ApiBanInfoNone, ApiBanInfoSome]]


CHUNK_SIZE = 200
BATCH_RE = re.compile(r"^(?:√|×)(\d+)(是云黑\.|是避雷\.|未记录)$")
CONFIG = configs.SharedConfig("qimeng", Config)
SEND_DATE_RE = re.compile(r"^(\d+)年(\d+)月(\d+)日(\d+)时(\d+)分(\d+)秒$")


def format_date(date: Optional[datetime]) -> str:
  return f"{date:%Y-%m-%d %H:%M:%S} 距今 {(datetime.now() - date).days} 天" if date else "无记录"


async def query_openapi(uid: int) -> tuple[int, str]:
  config = CONFIG()
  http = misc.http()
  params = {"key": config.token.get_secret_value(), "id": uid}
  async with http.get(config.host + "/OpenAPI/all_f.php", params=params) as response:
    data = ApiResult.model_validate(await response.json(content_type=None))
  data = data.info
  basic_info = f'''\
手机{'✓' if data[0].tel else '✗'} \
实名{'✓' if data[0].shiming else '✗'} \
微信{'✓' if data[0].wx else '✗'} \
支付宝{'✓' if data[0].zfb else '✗'}
所在群数：{data[1].group_num}
本月活跃：{data[1].m_send_num}
总计活跃：{data[1].send_num}
首次活跃：{format_date(data[1].first_send)}
最后活跃：{format_date(data[1].last_send)}'''
  if data[2].type == "bilei":
    type = 2
    detail = f'''\
账号为避雷/前科
登记老师：{data[2].admin}
避雷时间：{data[2].date:%Y-%m-%d %H:%M:%S}
避雷原因：{data[2].note}
{basic_info}'''
  elif data[2].type == "yunhei":
    type = 1
    detail = f'''\
帐号为云黑
登记老师：{data[2].admin}
云黑等级：{data[2].level}
上黑时间：{data[2].date:%Y-%m-%d %H:%M:%S}
云黑原因：{data[2].note}
{basic_info}'''
  else:
    type = 0
    detail = f"账号暂无云黑\n{basic_info}"
  return type, detail


async def query_spider_single(uid: int) -> tuple[int, str]:
  config = CONFIG()
  http = misc.http()
  async with http.post(
    # 非浏览器UA排版有问题
    config.host, data={"cxtype": "DanYi", "user": uid}, headers={"User-Agent": misc.BROWSER_UA},
  ) as response:
    parser = SingleParser()
    parser.feed(await response.text())
    parser.close()
    value = parser.getvalue()
  lines = value.splitlines()
  if lines[2] == "账号为避雷/前科,请谨慎交易":
    type = 2
  elif lines[2] == "警告!请立即请终止交易!!!":
    type = 1
  elif lines[2] == "账号暂无云黑,请谨慎判断":
    type = 0
  else:
    raise ValueError("无效数据")
  return type, value


async def query_spider_batch(uids: Collection[int]) -> list[tuple[int, int]]:
  config = CONFIG()
  http = misc.http()
  data = {"cxtype": "PiLiang", "user": "|".join(str(x) for x in uids)}
  async with http.post(config.host, data=data) as response:
    parser = BatchParser()
    parser.feed(await response.text())
    parser.close()
  result: list[tuple[int, int]] = []
  for line in parser.lines:
    if match := BATCH_RE.match(line):
      uid = int(match[1])
      if match[2] == "是避雷.":
        result.append((uid, 2))
      elif match[2] == "是云黑.":
        result.append((uid, 1))
      else:
        result.append((uid, 0))
    else:
      raise ValueError("无效数据")
  if len(result) != len(uids):
    raise ValueError("数据数量不匹配")
  return result


def query_usage() -> str:
  config = CONFIG()
  return f'''\
/查云黑 <QQ号> [<QQ号>...]
可以批量查询多个，最多 {CHUNK_SIZE} 个
数据来自 {config.host}'''

query = (
  command.CommandBuilder("qimeng.query", "查云黑")
  .brief("查询趣绮梦Furry云黑")
  .usage(query_usage)
  .throttle(5, 1)
  .help_condition(lambda _: bool(CONFIG().token))
  .rule(lambda: bool(CONFIG().token))
  .build()
)

@query.handle()
async def handle_query(args: Message = CommandArg()) -> None:
  uids: list[int] = []
  for seg in args:
    if seg.type == "text":
      for i in seg.data["text"].split():
        try:
          uids.append(int(i))
        except ValueError:
          await query.finish(f"{i} 不是QQ号")
    elif seg.type == "at":
      qq = seg.data["qq"]
      if qq == "all":
        await query.finish("请使用 /查群云黑 批量查询全体成员")
      uids.append(int(qq))
    else:
      await query.finish("只能传入QQ号或者@")
  if not uids:
    await query.finish(query.__doc__)
  config = CONFIG()
  if config.use_spider:
    if len(uids) > CHUNK_SIZE:
      await query.finish(f"查询数量过多，最多 {CHUNK_SIZE} 个")
    if len(uids) > 1:
      result = await query_spider_batch(uids)
      lines = []
      for uid, type in result:
        if type == 2:
          lines.append(f"⚠️ {uid} 位于避雷名单中。")
        elif type == 1:
          lines.append(f"🚨 {uid} 位于云黑名单中。")
        else:
          lines.append(f"✅ {uid} 无记录。")
      await query.finish("\n".join(lines))
    _, detail = await query_spider_single(uids[0])
    await query.finish(detail)
  else:
    if len(uids) > 1:
      await query.finish("抱歉，由于上游限制，OpenAPI 模式暂不支持批量查询。")
    _, detail = await query_openapi(uids[0])
    await query.finish(detail)


def query_all_usage() -> str:
  config = CONFIG()
  return f'''\
/查群云黑
10 秒内只能查询一次
数据来自 {config.host}'''

query_all = (
  command.CommandBuilder("qimeng.query_all", "查群云黑")
  .brief("批量查询本群群员云黑")
  .usage(query_all_usage)
  .throttle(1, 10)
  .in_group()
  .help_condition(lambda _: CONFIG().use_spider)
  .rule(lambda: CONFIG().use_spider)
  .build()
)

@query_all.handle()
async def handle_query_all(bot: Bot, event: Event) -> None:
  config = CONFIG()
  group_id = context.get_event_context(event)
  members = {
    uid: member["card"] or member["nickname"]
    for member in await bot.get_group_member_list(group_id=group_id)
    if (uid := member["user_id"]) not in config.ignore
  }
  chunks = math.ceil(len(members) / CHUNK_SIZE)
  if chunks > 1:
    await query_all.send(f"群员较多，需要分为 {chunks} 批次查询，请稍等。")
  result: list[tuple[int, int]] = []
  for chunk in misc.chunked(members, CHUNK_SIZE):
    if result:
      await asyncio.sleep(1)
    result.extend(await query_spider_batch(chunk))
  lines: list[str] = []
  for uid, type in result:
    if type == 2:
      lines.append(f"⚠️ {members[uid]}({uid}) 位于避雷名单中。")
    elif type == 1:
      lines.append(f"🚨 {members[uid]}({uid}) 位于云黑名单中。")
  if not lines:
    await query_all.finish("✅ 群内无云黑或避雷成员。")
  await query_all.finish("\n".join(lines))


def kick_all_usage() -> str:
  config = CONFIG()
  return f'''\
/踢群云黑 - 踢出所有云黑成员
/踢群云黑 避雷 - 踢出所有云黑和避雷成员
10 秒内只能使用一次
数据来自 {config.host}'''

kick_all = (
  command.CommandBuilder("qimeng.kick_all", "踢群云黑")
  .brief("批量踢出云黑成员")
  .usage(kick_all_usage)
  .throttle(1, 10)
  .in_group()
  .level("admin")
  .help_condition(lambda _: CONFIG().use_spider)
  .rule(lambda: CONFIG().use_spider)
  .build()
)

@kick_all.handle()
async def handle_kick_all(
  bot: Bot, event: Event, state: T_State, arg: Message = CommandArg(),
) -> None:
  config = CONFIG()
  group_id = context.get_event_context(event)
  members = {
    uid: member["card"] or member["nickname"]
    for member in await bot.get_group_member_list(group_id=group_id)
    if (uid := member["user_id"]) not in config.ignore
  }
  chunks = math.ceil(len(members) / CHUNK_SIZE)
  if chunks > 1:
    await kick_all.send(f"群员较多，需要分为 {chunks} 批次查询，请稍等。")
  result: list[tuple[int, int]] = []
  for chunk in misc.chunked(members, CHUNK_SIZE):
    if result:
      await asyncio.sleep(1)
    result.extend(await query_spider_batch(chunk))
  uids: list[int] = []
  lines: list[str] = []
  include_type2 = "避雷" in arg.extract_plain_text()
  for uid, type in result:
    if type == 2 and include_type2:
      lines.append(f"⚠️ {members[uid]}({uid}) 位于避雷名单中。")
      uids.append(uid)
    elif type == 1:
      lines.append(f"🚨 {members[uid]}({uid}) 位于云黑名单中。")
      uids.append(uid)
  if not lines:
    if include_type2:
      await kick_all.finish("✅ 群内无云黑或避雷成员。")
    else:
      await kick_all.finish("✅ 群内无云黑成员，要包括避雷成员，请发送“/踢群云黑 避雷”。")
  info = await bot.get_group_member_info(group_id=group_id, user_id=event.self_id)
  if info["role"] == "member":
    lines.append("IdhagnBot 不是群管理员，不能使用 /踢群云黑")
    await kick_all.finish("\n".join(lines))
  state["uids"] = uids
  lines.append("是否全部踢出？请发送“是”或“否”")
  await kick_all.send("\n".join(lines))

@kick_all.got("confirm")
async def got_confirm(bot: Bot, event: Event, state: T_State, confirm: str = ArgStr()) -> None:
  if confirm != "是":
    await kick_all.finish("操作取消")
  group_id = context.get_event_context(event)
  uids: list[int] = state["uids"]
  done, _ = await asyncio.wait([
    asyncio.create_task(bot.set_group_kick(group_id=group_id, user_id=uid)) for uid in uids
  ])
  success = sum(i.exception() is None for i in done)
  failed = len(uids) - success
  msg = f"成功踢出 {success} 个成员"
  if failed > 0:
    msg += f"，踢出 {failed} 个成员失败"
  await kick_all.finish(msg)


async def check_member_join(event: GroupIncreaseNoticeEvent) -> bool:
  config = CONFIG()
  return (
    bool(config.token)
    and event.user_id not in config.ignore
    and config.check_join[event.group_id]
  )

on_member_join = nonebot.on_notice(check_member_join)

@on_member_join.handle()
async def handle_member_join(bot: Bot, event: GroupIncreaseNoticeEvent) -> None:
  config = CONFIG()
  if config.use_spider:
    type, detail = await query_spider_single(event.user_id)
  else:
    type, detail = await query_openapi(event.user_id)
  if type == 0:
    return
  name = await context.get_card_or_name(bot, event, event.user_id)
  await on_member_join.finish(f'''⚠️ 警告 ⚠️
刚刚加群的用户 {name}({event.user_id}) 已上黑，请注意。
{detail}''')


async def check_group_request(event: GroupRequestEvent) -> bool:
  config = CONFIG()
  return (
    bool(config.token)
    and event.sub_type == "add"
    and event.user_id not in config.ignore
    and config.check_request[event.group_id]
  )

on_group_request = nonebot.on_notice(check_group_request)

@on_group_request.handle()
async def handle_group_request(bot: Bot, event: GroupRequestEvent) -> None:
  config = CONFIG()
  if config.use_spider:
    type, detail = await query_spider_single(event.user_id)
  else:
    type, detail = await query_openapi(event.user_id)
  if type == 0:
    return
  if config.reject_request[event.group_id]:
    await bot.set_group_add_request(
      flag=event.flag, sub_type=event.sub_type, approve=False, reason="云黑用户，机器人自动拒绝",
    )
  info = await bot.get_stranger_info(user_id=event.user_id)
  name = info["nickname"]
  await on_group_request.finish(f'''⚠️ 警告 ⚠️
请求加群的用户 {name}({event.user_id}) 已上黑，请管理员注意。
{detail}''')
