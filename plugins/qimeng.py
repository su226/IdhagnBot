import nonebot
from nonebot.adapters.onebot.v11 import Bot, GroupIncreaseNoticeEvent, GroupRequestEvent, Message
from nonebot.params import CommandArg
from pydantic import BaseModel

from util import command, config_v2, context, util


class Config(BaseModel):
  token: str = ""
  auto_reject: bool = False


API = "https://yunhei.qimeng.fun/OpenAPI.php?key={}&id={}"
URL = "https://yunhei.qimeng.fun/"
CONFIG = config_v2.SharedConfig("qimeng", Config)


async def query_uid(uid: int) -> str | None:
  config = CONFIG()
  http = util.http()
  async with http.get(API.format(config.token, uid)) as response:
    data = await response.json(content_type=None)  # text/html
  data = data["info"][0]
  if data["yh"] == "false":
    return None
  return data["note"]


async def check_query() -> bool:
  return bool(CONFIG().token)
USAGE = f"/查云黑 <QQ号>\n数据来自 {URL}"
query = command.CommandBuilder("qimeng.query", "查云黑") \
  .brief("查询趣绮梦Furry云黑") \
  .usage(USAGE) \
  .throttle(4) \
  .help_condition(lambda _: bool(CONFIG().token)) \
  .rule(check_query) \
  .build()
@query.handle()
async def handle_query(args: Message = CommandArg()) -> None:
  try:
    uid = int(args.extract_plain_text().rstrip())
  except ValueError:
    await query.finish(USAGE)
  reason = await query_uid(uid)
  if reason is None:
    await query.finish(f"查询账号：{uid}\n该用户未上黑，但并不保证绝对安全，请注意。")
  await query.finish(f"查询账号：{uid}\n该用户已上黑，原因为：" + reason)


async def check_member_join(_: GroupIncreaseNoticeEvent) -> bool:
  return bool(CONFIG().token)
on_member_join = nonebot.on_notice(check_member_join)
@on_member_join.handle()
async def handle_member_join(bot: Bot, event: GroupIncreaseNoticeEvent) -> None:
  reason = await query_uid(event.user_id)
  if reason is not None:
    name = await context.get_card_or_name(bot, event, event.user_id)
    await on_member_join.send(f'''⚠️ 警告 ⚠️
刚刚加群的用户 {name}({event.user_id}) 已上黑，请注意。
原因：{reason}
详情请参考 {URL}''')


async def check_group_request(event: GroupRequestEvent) -> bool:
  return bool(CONFIG().token) and event.sub_type == "add"
on_group_request = nonebot.on_notice(check_group_request)
@on_group_request.handle()
async def handle_group_request(bot: Bot, event: GroupRequestEvent) -> None:
  reason = await query_uid(event.user_id)
  if reason is not None:
    info = await bot.get_stranger_info(user_id=event.user_id)
    name = info["nickname"]
    await on_group_request.send(f'''⚠️ 警告 ⚠️
请求加群的用户 {name}({event.user_id}) 已上黑，请管理员注意。
原因：{reason}
详情请参考 {URL}''')
    config = CONFIG()
    if config.auto_reject:
      await bot.set_group_add_request(
        flag=event.flag, sub_type=event.sub_type, approve=False, reason="云黑用户，机器人自动拒绝"
      )


# 公共 API 提供的接口和数据似乎有点少
# 从网页查询有上黑等级、上黑时间、上黑原因和登记人，但使用 API 查询只有上黑原因
# 并且没有批量查询，没法写查询全群
# 抱歉，我尽力了，我也只有等待上游更新
