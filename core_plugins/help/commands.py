from core_plugins.context.typing import Context
from .item import find_command, format_page
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg
import nonebot

context: Context = nonebot.require("context")

help = nonebot.on_command("帮助", aliases={"help", "?"})
help.__cmd__ = "帮助"
help.__brief__ = "查看本帮助"
help.__doc__ = '''
{cmd} - 查看第一页帮助
{cmd} <页码> - 查看指定页帮助
{cmd} <命令名> - 查看命令帮助'''
@help.handle()
async def handle_help(bot: Bot, event: Event, args: Message = CommandArg()):
  args = str(args).rstrip()
  private = not hasattr(event, "group_id")
  ctx = context.get_context(event)
  permission = await context.get_permission(bot, event)
  if len(args) == 0:
    await help.send(Message(format_page(1, ctx, private, permission)))
    return
  try:
    page = int(args)
  except:
    pass
  else:
    await help.send(Message(format_page(page, ctx, private, permission)))
    return
  command = find_command(args, private, ctx, permission)
  if command:
    await help.send(Message(command.usage))
    return
  await help.send("无此帮助条目、权限不足或在当前上下文不可用")
