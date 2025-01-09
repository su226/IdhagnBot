import asyncio
import math
import re
from html.parser import HTMLParser
from io import StringIO
from typing import List, Optional, Set, Tuple, cast

import nonebot
from nonebot.adapters.onebot.v11 import (
  Bot, Event, GroupIncreaseNoticeEvent, GroupRequestEvent, Message,
)
from nonebot.params import ArgStr, CommandArg
from nonebot.typing import T_State
from pydantic import BaseModel, Field, SecretStr

from util import command, configs, context, misc


class Config(BaseModel):
  # 公共 API 提供的接口和数据似乎有点少
  # 从网页查询有上黑等级、上黑时间、上黑原因和登记人，但使用 API 查询只有上黑原因
  # 并且没有批量查询，没法写查询全群
  # 对不起绮梦老师了
  host: str = "https://fz.qimeng.fun"
  api: str = "http://yunhei.qimeng.fun:12301/OpenAPI.php"
  token: SecretStr = SecretStr("")
  check_join: misc.EnableSet = misc.EnableSet.false()
  check_request: misc.EnableSet = misc.EnableSet.false()
  reject_request: misc.EnableSet = misc.EnableSet.false()
  # 默认忽略Q群管家
  ignore: Set[int] = Field(default_factory=lambda: {2854196310})

  @property
  def spider_version(self) -> int:
    if self.token.get_secret_value() in ("spider", "spider_v2"):
      return 2
    if self.token.get_secret_value() == "spider_v1":
      return 1
    return 0


class SingleV2Parser(HTMLParser):
  def __init__(self) -> None:
    super().__init__()
    self.level = 0
    self.in_script = False
    self.text = StringIO()

  def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
    if self.level:
      if tag == "script":
        self.in_script = True
      self.level += 1
    elif ("class", "header-img") in attrs:
      self.level = 2

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


class SingleV1Parser(HTMLParser):
  def __init__(self) -> None:
    super().__init__()
    self.level = 0
    self.text = StringIO()

  def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
    if self.level:
      if tag == "br":
        self.text.write("\n")
      else:
        self.level += 1
    elif attrs == [("id", "CheckText")]:
      self.level = 1

  def handle_data(self, data: str) -> None:
    if self.level:
      self.text.write(data.strip())

  def handle_endtag(self, tag: str) -> None:
    if self.level and tag != "br":
      self.level -= 1
    # center 是块级元素
    if self.level and tag == "center":
      self.text.write("\n")

  def getvalue(self) -> str:
    return self.text.getvalue().rstrip()


class BatchParser(HTMLParser):
  def __init__(self) -> None:
    super().__init__()
    self.begin = False
    self.lines: List[str] = []

  def handle_data(self, data: str) -> None:
    data = data.strip()
    if data == "---------查询结果---------":
      self.begin = True
    elif data == "------------------------------":
      self.begin = False
    elif self.begin and data:
      self.lines.append(data)


CHUNK_SIZE = 200
INT_RE = re.compile(r"\d+")
CONFIG = configs.SharedConfig("qimeng", Config)


async def query_openapi(uid: int) -> Tuple[int, str]:
  config = CONFIG()
  http = misc.http()
  params = {"key": config.token.get_secret_value(), "id": uid}
  async with http.get(config.api, params=params) as response:
    data = await response.json(content_type=None)  # text/html
  data = data["info"][0]
  if data["type"] == "bilei":
    type = 2
    detail = f'''\
账号为避雷/前科
登记老师:{data["admin"]}
避雷时间:{data["date"]}
避雷原因:{data["note"]}'''
  elif data["type"] == "yunhei":
    type = 1
    detail = f'''\
帐号为云黑
登记老师:{data["admin"]}
云黑等级:{data["level"]}
上黑时间:{data["date"]}
云黑原因:{data["note"]}'''
  else:
    type = 0
    detail = "账号暂无云黑"
  return type, detail


async def query_spider_single_v2(uid: int) -> Tuple[int, str]:
  config = CONFIG()
  http = misc.http()
  async with http.get(
    # 非浏览器UA排版有问题
    config.host, params={"user": uid}, headers={"User-Agent": misc.BROWSER_UA},
  ) as response:
    parser = SingleV2Parser()
    parser.feed(await response.text())
    parser.close()
    value = parser.getvalue()
  if "避雷时间" in value:
    type = 2
  elif "上黑时间" in value:
    type = 1
  else:
    type = 0
  return type, value


async def query_spider_single_v1(uid: int) -> Tuple[int, str]:
  config = CONFIG()
  http = misc.http()
  async with http.post(config.host + "/oldindex.php", data={"qq": uid}) as response:
    parser = SingleV1Parser()
    parser.feed(await response.text())
    parser.close()
    value = parser.getvalue()
  if "避雷起始时间" in value:
    type = 2
  elif "上黑等级" in value:
    type = 1
  else:
    type = 0
  return type, value


async def query_spider_batch(uids: List[int]) -> List[Tuple[int, int]]:
  config = CONFIG()
  http = misc.http()
  data = {"qq": "\n".join(str(x) for x in uids)}
  async with http.post(config.host + "/Piliang.php", data=data) as response:
    parser = BatchParser()
    parser.feed(await response.text())
    parser.close()
  result: List[Tuple[int, int]] = []
  for line in parser.lines:
    uid = int(cast(re.Match[str], INT_RE.search(line))[0])
    if line.endswith("避雷."):
      result.append((uid, 2))
    elif line.endswith("云黑."):
      result.append((uid, 1))
    else:
      result.append((uid, 0))
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
  uids: List[int] = []
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
  if config.spider_version:
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
    if config.spider_version == 2:
      _, detail = await query_spider_single_v2(uids[0])
      await query.finish(detail)
    _, detail = await query_spider_single_v1(uids[0])
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
  .help_condition(lambda _: CONFIG().spider_version != 0)
  .rule(lambda: CONFIG().spider_version != 0)
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
  result: List[Tuple[int, int]] = []
  for chunk in misc.chunked(members, CHUNK_SIZE):
    if result:
      await asyncio.sleep(1)
    result.extend(await query_spider_batch(chunk))
  lines: List[str] = []
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
  .help_condition(lambda _: CONFIG().spider_version != 0)
  .rule(lambda: CONFIG().spider_version != 0)
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
  result: List[Tuple[int, int]] = []
  for chunk in misc.chunked(members, CHUNK_SIZE):
    if result:
      await asyncio.sleep(1)
    result.extend(await query_spider_batch(chunk))
  uids: List[int] = []
  lines: List[str] = []
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
  uids: List[int] = state["uids"]
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
  if config.spider_version == 2:
    type, detail = await query_spider_single_v2(event.user_id)
  elif config.spider_version == 1:
    type, detail = await query_spider_single_v1(event.user_id)
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
  if config.spider_version == 2:
    type, detail = await query_spider_single_v2(event.user_id)
  elif config.spider_version == 1:
    type, detail = await query_spider_single_v1(event.user_id)
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
