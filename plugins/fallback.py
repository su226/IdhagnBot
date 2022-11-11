import nonebot
from aiohttp.client_exceptions import ClientError
from nonebot.adapters.onebot.v11 import ActionFailed, Bot, Event, Message, MessageEvent
from nonebot.message import event_postprocessor, run_postprocessor, run_preprocessor
from nonebot.params import CommandArg
from nonebot.typing import T_State

from util import command, context, misc


class ManualException(Exception):
  def __init__(self):
    super().__init__("管理员使用 /raise 手动触发了错误")


suppressed: set[int] = set()
driver = nonebot.get_driver()


@run_preprocessor
async def pre_run(state: T_State):
  if state.get("_as_command", True):
    state["_prefix"]["run"] = True


@run_postprocessor
async def post_run(bot: Bot, event: MessageEvent, e: Exception):
  group_id = getattr(event, "group_id", None)
  if isinstance(e, ActionFailed) and e.info.get("msg", None) == "SEND_MSG_API_ERROR":
    reason = "消息发送失败"
  elif isinstance(e, ClientError):
    reason = "网络错误"
  elif isinstance(e, ManualException):
    reason = "手动触发"
  elif isinstance(e, misc.PromptTimeout):
    reason = "等待回应超时"
  else:
    reason = "未知内部错误"
  result = f"机器人出错\n可能原因：{reason}"
  if group_id is None:
    await bot.send(event, result)
  elif group_id not in suppressed:
    await bot.send(event, result + "\n[群管] /suppress true - 禁用错误消息")
  user_id = getattr(event, "user_id", None)
  superusers = list(misc.superusers())
  if user_id not in superusers:
    message = str(event.message)
    if len(message) > 50:
      message = message[:50] + "…"
    notify = result + f"\n群聊: {group_id}, 用户: {user_id}, 消息:\n" + message
    for user in superusers:
      await bot.send_private_msg(user_id=user, message=notify)


@event_postprocessor
async def post_event(bot: Bot, event: Event, state: T_State) -> None:
  if not isinstance(event, MessageEvent):
    return
  group_id = getattr(event, "group_id", None)
  if group_id in suppressed or "run" in state["_prefix"]:
    return
  if misc.is_command(event.message):
    await bot.send(event, "命令不存在、权限不足或不适用于当前上下文")
  elif event.is_tome():
    await bot.send(event, "本帐号为机器人，请发送 /帮助 查看可用命令（可以不@）")


suppress = (
  command.CommandBuilder("fallback.suppress", "suppress")
  .in_group()
  .level("admin")
  .brief("暂时禁用错误消息")
  .usage('''\
/suppress - 查看是否已禁用本群错误消息
/suppress true - 禁用本群错误消息
/suppress false - 重新启用本群错误消息''')
  .build()
)
@suppress.handle()
async def handle_suppress(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
  value = str(args).rstrip()
  ctx = context.get_event_context(event)
  if not value:
    status = "已" if ctx in suppressed else "未"
    await suppress.finish(f"本群错误消息{status}被禁用")
  elif value in ("true", "t", "1", "yes", "y", "on"):
    suppressed.add(ctx)
    await suppress.finish("已禁用本群错误消息")
  elif value in ("false", "f", "0", "no", "n", "off"):
    suppressed.remove(ctx)
    await suppress.finish("已恢复本群错误消息")
  await suppress.finish(suppress.__doc__)

RAISE_USAGE = "/raise confirm - 手动触发一个错误"
raise_ = (
  command.CommandBuilder("fallback.raise", "raise")
  .level("admin")
  .in_group()
  .brief("手动触发一个错误")
  .build())


@raise_.handle()
async def handle_raise(args: Message = CommandArg()):
  if str(args).rstrip() == "confirm":
    raise ManualException
  await raise_.finish(RAISE_USAGE)
