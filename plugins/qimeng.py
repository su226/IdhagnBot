import asyncio
import math
import re
from html.parser import HTMLParser
from io import StringIO
from typing import List, Optional, Tuple, cast

import nonebot
from nonebot.adapters.onebot.v11 import (
  Bot, Event, GroupIncreaseNoticeEvent, GroupRequestEvent, Message
)
from nonebot.params import CommandArg
from pydantic import BaseModel, SecretStr

from util import command, configs, context, misc


class Config(BaseModel):
  # 公共 API 提供的接口和数据似乎有点少
  # 从网页查询有上黑等级、上黑时间、上黑原因和登记人，但使用 API 查询只有上黑原因
  # 并且没有批量查询，没法写查询全群
  # 对不起绮梦老师了
  token: SecretStr = SecretStr("")
  auto_reject: bool = False

  @property
  def use_spider(self) -> bool:
    return self.token.get_secret_value() == "spider"


class SingleParser(HTMLParser):
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


API = "https://yunhei.qimeng.fun/OpenAPI.php?key={}&id={}"
URL = "https://yunhei.qimeng.fun/"
BATCH_URL = "https://yunhei.qimeng.fun/Piliang.php"
CHUNK_SIZE = 200
INT_RE = re.compile(r"\d+")
CONFIG = configs.SharedConfig("qimeng", Config)


async def query_openapi(uid: int) -> Optional[str]:
  config = CONFIG()
  http = misc.http()
  async with http.get(API.format(config.token.get_secret_value(), uid)) as response:
    data = await response.json(content_type=None)  # text/html
  data = data["info"][0]
  if data["yh"] == "false":
    return None
  return data["note"]


async def query_spider(uid: int) -> Tuple[int, str]:
  http = misc.http()
  data = {"qq": uid}
  async with http.post(URL, data=data) as response:
    parser = SingleParser()
    parser.feed(await response.text())
    parser.close()
  value = parser.text.getvalue()
  if "避雷起始时间" in value:
    type = 2
  elif "上黑等级" in value:
    type = 1
  else:
    type = 0
  return type, value


async def query_spider_batch(uids: List[int]) -> List[Tuple[int, int]]:
  http = misc.http()
  data = {"qq": "\n".join(str(x) for x in uids)}
  async with http.post(BATCH_URL, data=data) as response:
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


query = (
  command.CommandBuilder("qimeng.query", "查云黑")
  .brief("查询趣绮梦Furry云黑")
  .usage(f'''\
/查云黑 <QQ号> [<QQ号>...]
可以批量查询多个
数据来自 {URL}''')
  .throttle(5, 1)
  .help_condition(lambda _: bool(CONFIG().token))
  .rule(lambda: bool(CONFIG().token))
  .build()
)
@query.handle()
async def handle_query(args: Message = CommandArg()) -> None:
  try:
    uids = [int(x) for x in args.extract_plain_text().split()]
  except ValueError:
    uids = []
  if not uids:
    await query.finish(query.__doc__)
  config = CONFIG()
  if config.use_spider:
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
    else:
      _, detail = await query_spider(uids[0])
      await query.finish(detail)
  else:
    if len(uids) > 1:
      await query.finish("抱歉，由于上游限制，OpenAPI 模式暂不支持批量查询。")
    uid = uids[0]
    reason = await query_openapi(uid)
    if reason is None:
      await query.finish(f"查询账号：{uid}\n该用户未上黑，但并不保证绝对安全。")
    await query.finish(f"查询账号：{uid}\n该用户已上黑，原因为：" + reason)


query_all = (
  command.CommandBuilder("qimeng.query_all", "查群云黑")
  .brief("批量查询本群群员云黑")
  .usage(f'''\
/查群云黑
10 秒内只能查询一次
数据来自 {URL}''')
  .throttle(1, 10)
  .in_group()
  .help_condition(lambda _: CONFIG().use_spider)
  .rule(lambda: CONFIG().use_spider)
  .build()
)
@query_all.handle()
async def handle_query_all(bot: Bot, event: Event) -> None:
  group_id = context.get_event_context(event)
  members = await bot.get_group_member_list(group_id=group_id)
  chunks = math.ceil(len(members) / CHUNK_SIZE)
  if chunks > 1:
    await query_all.send(f"群员较多，需要分为 {chunks} 批次查询，请稍等。")
  result: List[Tuple[int, int]] = []
  for chunk in misc.chunked([member["user_id"] for member in members], CHUNK_SIZE):
    if result:
      await asyncio.sleep(1)
    result.extend(await query_spider_batch(chunk))
  lines: List[str] = []
  for uid, type in result:
    if type == 2:
      lines.append(f"⚠️ {uid} 位于避雷名单中。")
    elif type == 1:
      lines.append(f"🚨 {uid} 位于云黑名单中。")
  if not lines:
    lines.append("✅ 群内无云黑成员。")
  await query_all.finish("\n".join(lines))


async def check_member_join(_: GroupIncreaseNoticeEvent) -> bool:
  return bool(CONFIG().token)
on_member_join = nonebot.on_notice(check_member_join)
@on_member_join.handle()
async def handle_member_join(bot: Bot, event: GroupIncreaseNoticeEvent) -> None:
  config = CONFIG()
  if config.use_spider:
    type, detail = await query_spider(event.user_id)
    if type == 0:
      return
  else:
    reason = await query_openapi(event.user_id)
    if reason is None:
      return
    detail = f"原因：{reason}\n详情请参考 {URL}"
  name = await context.get_card_or_name(bot, event, event.user_id)
  await on_member_join.finish(f'''⚠️ 警告 ⚠️
刚刚加群的用户 {name}({event.user_id}) 已上黑，请注意。
{detail}''')


async def check_group_request(event: GroupRequestEvent) -> bool:
  return bool(CONFIG().token) and event.sub_type == "add"
on_group_request = nonebot.on_notice(check_group_request)
@on_group_request.handle()
async def handle_group_request(bot: Bot, event: GroupRequestEvent) -> None:
  config = CONFIG()
  if config.use_spider:
    type, detail = await query_spider(event.user_id)
    if type == 0:
      return
  else:
    reason = await query_openapi(event.user_id)
    if reason is None:
      return
    detail = f"原因：{reason}\n详情请参考 {URL}"
  if config.auto_reject:
    await bot.set_group_add_request(
      flag=event.flag, sub_type=event.sub_type, approve=False, reason="云黑用户，机器人自动拒绝"
    )
  info = await bot.get_stranger_info(user_id=event.user_id)
  name = info["nickname"]
  await on_group_request.finish(f'''⚠️ 警告 ⚠️
请求加群的用户 {name}({event.user_id}) 已上黑，请管理员注意。
{detail}''')
