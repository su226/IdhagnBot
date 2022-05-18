from typing import Iterable, Generator

from aiohttp.client_exceptions import ClientError
from pydantic import Field
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, ActionFailed
from nonebot.message import run_preprocessor, run_postprocessor, event_postprocessor
from nonebot.params import CommandArg
from nonebot.typing import T_State
import nonebot

from util import context, command, permission
from util.config import BaseState

class State(BaseState):
  __file__ = "fallback"
  suppress: set[int] = Field(default_factory=set)

STATE = State.load()

class ManualException(Exception):
  def __init__(self):
    super().__init__("管理员使用 /raise 手动触发了错误")

driver = nonebot.get_driver()

@run_preprocessor
async def pre_run(state: T_State):
  state["_prefix"]["run"] = True

def convert_superusers(superusers: Iterable[str]) -> Generator[int, None, None]:
  for i in superusers:
    if i.startswith(permission.ADAPTER_NAME):
      yield int(i[len(permission.ADAPTER_NAME) + 1:])
    else:
      try:
        yield int(i)
      except ValueError:
        pass

@run_postprocessor
async def post_run(bot: Bot, event: MessageEvent, e: Exception):
  group_id = getattr(event, "group_id", None)
  if isinstance(e, ActionFailed) and e.info.get("msg", None) == "SEND_MSG_API_ERROR":
    reason = "消息发送失败"
  elif isinstance(e, ClientError):
    reason = "网络错误"
  elif isinstance(e, ManualException):
    reason = "手动触发"
  else:
    reason = "未知内部错误"
  result = f"机器人出错\n可能原因：{reason}"
  if group_id is None:
    await bot.send(event, result)
  elif group_id not in STATE.suppress:
    # await bot.send(event, result + "\n[群管] /suppress true - 禁用错误消息")
    await bot.send(event, result + "\n/report [可选说明] - 反馈Bug")
  user_id = getattr(event, "user_id", None)
  superusers = list(convert_superusers(driver.config.superusers))
  if user_id not in superusers:
    for user in superusers:
      await bot.send_private_msg(user_id=user, message=result + f"\n群聊: {group_id}, 用户: {user_id}")

@event_postprocessor
async def post_event(bot: Bot, event: MessageEvent, state: T_State):
  prefix = state["_prefix"]
  if "special" not in prefix and (prefix["command"] is None or "run" not in prefix):
    if event.message.extract_plain_text().lstrip().startswith("/"):
      await bot.send(event, "命令不存在、权限不足或不适用于当前上下文")
    elif event.is_tome():
      await bot.send(event, "本帐号为机器人，请发送 /帮助 查看可用命令（可以不@）")

SUPPRESS_USAGE = '''\
/suppress - 查看是否已禁用本群错误消息
/suppress true - 禁用本群错误消息
/suppress false - 重新启用本群错误消息'''
suppress = (command.CommandBuilder("fallback.suppress", "suppress")
  .in_group()
  .level("admin")
  .brief("暂时禁用错误消息")
  .usage(SUPPRESS_USAGE)
  .build())
@suppress.handle()
async def handle_suppress(bot: Bot, event: MessageEvent, args = CommandArg()):
  value = str(args).rstrip()
  ctx = context.get_event_context(event)
  if not value:
    suppressed = "已" if ctx in STATE.suppress else "未"
    await suppress.send(f"本群错误消息{suppressed}被禁用")
  elif value in ("true", "t", "1", "yes", "y", "on"):
    STATE.suppress.add(ctx)
    STATE.dump()
    await suppress.send(f"已禁用本群错误消息")
  elif value in ("false", "f", "0", "no", "n", "off"):
    STATE.suppress.remove(ctx)
    STATE.dump()
    await suppress.send(f"已恢复本群错误消息")
  else:
    await suppress.send(SUPPRESS_USAGE)

RAISE_USAGE = "/raise confirm - 手动触发一个错误"
raise_ = (command.CommandBuilder("fallback.raise", "raise")
  .level("admin")
  .in_group()
  .brief("手动触发一个错误")
  .build())
@raise_.handle()
async def handle_raise(args = CommandArg()):
  if str(args).rstrip() == "confirm":
    raise ManualException
  await raise_.send(RAISE_USAGE)
