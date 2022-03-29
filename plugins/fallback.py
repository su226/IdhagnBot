from util.config import BaseState, Field
from util import context
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.message import run_preprocessor, run_postprocessor, event_postprocessor
from nonebot.params import State as BotState, CommandArg
import nonebot

class State(BaseState):
  __file__ = "fallback"
  suppress: set[int] = Field(default_factory=set)

STATE = State.load()

driver = nonebot.get_driver()

@run_preprocessor
async def pre_run(state = BotState()):
  state["_prefix"]["run"] = True

@run_postprocessor
async def post_run(bot: Bot, event: MessageEvent, _: Exception):
  group_id = getattr(event, "group_id", None)
  if group_id is None:
    user_id = getattr(event, "user_id", -1)
    str_user_id = str(user_id)
    if not any(i in (user_id, str_user_id) for i in driver.config.superusers):
      await bot.send(event, "机器人出错，请尝试联系开发者")
  elif group_id not in STATE.suppress:
    await bot.send(event, "机器人出错，请尝试联系开发者（如果本消息刷屏，群管理员可发送 /suppress true 来禁用）")
  for user in driver.config.superusers:
    await bot.send_private_msg(user_id=user, message=f"机器人出错，请及时查看日志并维修！")

@event_postprocessor
async def post_event(bot: Bot, event: MessageEvent, state = BotState()):
  if "run" not in state["_prefix"]:
    if event.message.extract_plain_text().lstrip().startswith("/"):
      await bot.send(event, "命令不存在、权限不足或不适用于当前上下文")
    elif event.is_tome():
      await bot.send(event, "本帐号为机器人，请发送 /帮助 查看可用命令（不需要@）")

suppress = nonebot.on_command("suppress", context.in_context_rule(context.ANY_GROUP), permission=context.Permission.ADMIN)
suppress.__cmd__ = "suppress"
suppress.__brief__ = "暂时禁用错误消息"
suppress.__doc__ = '''\
/suppress - 查看是否已禁用本群错误消息
/suppress true - 禁用本群错误消息
/suppress false - 重新启用本群错误消息'''
suppress.__ctx__ = [context.ANY_GROUP]
suppress.__perm__ = context.Permission.ADMIN
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
    await suppress.send(suppress.__doc__)

raise_ = nonebot.on_command("raise", permission=context.Permission.ADMIN)
raise_.__cmd__ = "raise"
raise_.__brief__ = "手动触发一个错误"
raise_.__doc__ = "/raise confirm - 手动触发一个错误"
raise_.__ctx__ = [context.ANY_GROUP]
raise_.__perm__ = context.Permission.ADMIN
@raise_.handle()
async def handle_raise(args = CommandArg()):
  if str(args).rstrip() == "confirm":
    raise Exception("管理员使用 /raise 手动触发了错误")
  await raise_.send(raise_.__doc__)
