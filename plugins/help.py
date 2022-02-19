from util import context, help
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg
import nonebot

help_cmd = nonebot.on_command("帮助", aliases={"help", "?"})
help_cmd.__cmd__ = "帮助"
help_cmd.__brief__ = "查看本帮助"
help_cmd.__doc__ = '''
{cmd} - 查看第一页帮助
{cmd} <页码> - 查看指定页帮助
{cmd} <命令名> - 查看命令帮助'''
@help_cmd.handle()
async def handle_help(bot: Bot, event: Event, args: Message = CommandArg()):
  args = str(args).rstrip()
  private = not hasattr(event, "group_id")
  ctx = context.get_event_context(event)
  permission = await context.get_permission(bot, event)
  if len(args) == 0:
    await help_cmd.finish(Message(help.format_page(1, ctx, private, permission)))
  try:
    page = int(args)
  except:
    pass
  else:
    await help_cmd.finish(Message(help.format_page(page, ctx, private, permission)))
  command = help.find_command(args, private, ctx, permission)
  if command:
    await help_cmd.finish(Message(command.usage))
  await help_cmd.send("无此帮助条目、权限不足或在当前上下文不可用")
