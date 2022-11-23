import asyncio
from typing import Set

import nonebot
from aiohttp.client_exceptions import ClientError
from nonebot.adapters.onebot.v11 import ActionFailed, Bot, Event, Message, MessageEvent
from nonebot.message import event_postprocessor, run_postprocessor, run_preprocessor
from nonebot.params import CommandArg
from nonebot.typing import T_State
from PIL import Image

from util import command, context, imutil, misc, textutil


class ManualException(Exception):
  def __init__(self):
    super().__init__("管理员使用 /raise 手动触发了错误")


suppressed: Set[int] = set()
driver = nonebot.get_driver()


@run_preprocessor
async def pre_run(state: T_State):
  if state.get("_as_command", True):
    state["_prefix"]["run"] = True


async def try_send(bot: Bot, user: int, message: str) -> None:
  try:
    await bot.send_private_msg(user_id=user, message=message)
  except ActionFailed:
    pass


@run_postprocessor
async def post_run(bot: Bot, event: MessageEvent, e: Exception):
  if isinstance(e, ActionFailed) and e.info.get("msg", None) == "SEND_MSG_API_ERROR":
    reason = "消息发送失败"
    explain = "可能是发送的内容过长、图片过大、含有敏感内容或者机器人帐号被风控。"
  elif isinstance(e, ClientError):
    reason = "网络错误"
    explain = "可能是命令使用的在线 API 不稳定，或者机器人服务器的网络问题。"
  elif isinstance(e, ManualException):
    reason = "管理员手动触发"
    explain = "如果你不是群管理员，可以忽略这个。"
  elif isinstance(e, misc.PromptTimeout):
    reason = "等待回应超时"
    explain = "请及时发送消息回应机器人。"
  else:
    reason = "未知错误"
    explain = "这可能是 IdhagnBot 的设计缺陷，请向开发者寻求帮助。"

  group_id = getattr(event, "group_id", None)
  if group_id not in suppressed:
    markup = '''\
  <span weight='heavy' size='200%'>这个要慌，问题很大</span>
  <span color='#ffffff88'>Something really bad happens. Panic!</span>'''
    header = textutil.render(markup, "sans", 32, color=(255, 255, 255), align="m", markup=True)

    markup = f'''\
<b>IdhagnBot 遇到了一个内部错误。</b>
<span color='#f5f543'>可能原因: </span>{reason}
{explain}'''
    fallback = f"IdhagnBot 遇到了一个内部错误。\n可能原因：{reason}\n{explain}"
    if group_id is not None:
      markup += (
        "\n<span color='#29b8db'>提示: </span>"
        "群管理员可以发送 /suppress true 暂时禁用本群错误消息。"
      )
      fallback += "\n群管理员可以发送 /suppress true 暂时禁用本群错误消息。"
    content = textutil.render(
      markup, "span", 32, color=(255, 255, 255), box=max(640, header.width), markup=True
    )

    size = (max(header.width, content.width) + 64, header.height + content.height + 80)
    im = Image.new("RGB", size, (30, 30, 30))
    im.paste((205, 49, 49), (0, 32, im.width, 32 + header.height))
    imutil.paste(im, header, (im.width // 2, 32), anchor="mt")
    im.paste(content, (32, 48 + header.height), content)
    segment = imutil.to_segment(im)
    try:
      await bot.send(event, segment)
    except ActionFailed:
      await bot.send(event, fallback)

  exc_type = type(e)
  exc_typename = exc_type.__qualname__
  exc_mod = exc_type.__module__
  if exc_mod not in ("__main__", "builtins"):
    if not isinstance(exc_mod, str):
      exc_mod = "<unknown>"
    exc_typename = exc_mod + '.' + exc_typename
  try:
    exc_info = str(e)
  except Exception:
    exc_info = ""

  user_id = getattr(event, "user_id", None)
  superusers = list(misc.superusers())
  if user_id not in superusers:
    message = str(event.message)
    if len(message) > 50:
      message = message[:50] + "…"
    notify = f"机器人出错 - {reason}\n{exc_typename}"
    if exc_info:
      notify += f": {exc_info}"
    notify += f"\n群聊: {group_id}\n用户: {user_id}\n消息: {message}"
    await asyncio.gather(*(try_send(bot, user, notify) for user in superusers))


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
