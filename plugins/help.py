from util import context, help
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg
import nonebot

help_cmd = nonebot.on_command("帮助", aliases={"help", "?"})
help_cmd.__cmd__ = ["帮助", "help", "?"]
help_cmd.__brief__ = "查看所有帮助"
help_cmd.__doc__ = '''\
/帮助 [...分类] [页码] - 查看帮助页
/帮助 <命令名> - 查看命令帮助
帮助页中以点号开头的是分类，以斜线开头的是命令
分类和命令前面的符号仅用作区分，查看时无需输入
命令帮助中尖括号里的参数必选，方括号里的参数可选，带...的参数可输入多个'''
@help_cmd.handle()
async def handle_help(bot: Bot, event: Event, msg: Message = CommandArg()):
  args = str(msg).split()
  private = not hasattr(event, "group_id")
  ctx = context.get_event_context(event)
  permission = await context.get_permission(bot, event)
  if len(args) == 0:
    await help_cmd.finish(Message(help.CategoryItem.ROOT.format_page(1, ctx, private, permission)))
  elif len(args) == 1:
    command = help.CommandItem.find(args[0], private, ctx, permission)
    if command:
      await help_cmd.finish(Message(command.usage))
  try:
    page = int(args[-1])
    path = args[:-1]
  except:
    page = 1
    path = args
  try:
    result = help.CategoryItem.find(path).format_page(page, ctx, private, permission)
  except:
    result = "无此条目或分类、权限不足或在当前上下文不可用"
  await help_cmd.finish(Message(result))
