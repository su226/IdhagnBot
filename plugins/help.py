import asyncio
from typing import List, Optional

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg

from util import command, context, help, misc


async def get_available_groups(bot: Bot, user_id: int) -> List[int]:
  async def in_group(group_id: int) -> int:
    try:
      await bot.get_group_member_info(group_id=group_id, user_id=user_id)
    except ActionFailed:
      return 0
    else:
      return group_id
  coros = [in_group(group) for group in context.CONFIG().groups]
  groups = await asyncio.gather(*coros)
  return [group for group in groups if group]


def find_command(name: str) -> Optional[help.CommandItem]:
  try:
    return help.CommandItem.find(name)
  except KeyError:
    pass
  if name.startswith("/"):
    try:
      return help.CommandItem.find(name[1:])
    except KeyError:
      pass


def normalize_path(path: List[str]) -> List[str]:
  result: List[str] = []
  for i in path:
    result.extend(x for x in i.split(".") if x)
  return result


help_cmd = (
  command.CommandBuilder("help", "帮助", "help", "?")
  .brief("查看所有帮助")
  .usage('''\
/帮助 [...分类] [页码] - 查看帮助页
/帮助 <命令名> - 查看命令帮助
帮助页中以点号开头的是分类，以斜线开头的是命令
分类和命令前面的符号仅用作区分，查看时无需输入
命令帮助中尖括号里的参数必选，方括号里的参数可选，带...的参数可输入多个''')
  .build()
)
@help_cmd.handle()
async def handle_help(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
  args = msg.extract_plain_text().split()
  private = not hasattr(event, "group_id")
  current_group = context.get_event_context(event)
  if private:
    available_groups = await get_available_groups(bot, event.user_id)
  else:
    available_groups = [current_group]
  data = help.ShowData(
    user_id=event.user_id,
    current_group=current_group,
    available_groups=available_groups,
    private=private,
    level=await context.get_event_level(bot, event),
  )
  if len(args) == 0:
    bot_name = await context.get_card_or_name(bot, event, event.self_id)
    nodes = help.CategoryItem.ROOT.format(data, [], event.self_id, bot_name)
    await misc.send_forward_msg(bot, event, *nodes)
    await help_cmd.finish()
  elif len(args) == 1:
    if (command := find_command(args[0])):
      await help_cmd.finish(Message(command.format()))
  try:
    path = normalize_path(args)
    category = help.CategoryItem.find(path, check=data)
    bot_name = await context.get_card_or_name(bot, event, event.self_id)
    nodes = category.format(data, path, event.self_id, bot_name)
    await misc.send_forward_msg(bot, event, *nodes)
    await help_cmd.finish()
  except (KeyError, ValueError):
    pass
  await help_cmd.finish("无此条目或分类、权限不足或在当前上下文不可用")
