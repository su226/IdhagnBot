import os
import random
import re

from nonebot.adapters import Message
from nonebot.params import CommandArg

from util import command

from . import strfile

RE_033 = re.compile("\033\\[(\\d*;?)*m")


def list_fortunes() -> list[str]:
  return [
    i.name for i in os.scandir("/usr/share/fortune") if i.is_file() and not i.name.endswith(".dat")]


def strip_033(src: str) -> str:
  return RE_033.sub("", src)


fortune = (
  command.CommandBuilder("fortune", "fortune")
  .brief("随机显示一条希望有用的格言")
  .usage('''\
/fortune - 显示一条随机格言
/fortune [...来源] - 显示一条指定来源之一的格言
/fortune ls - 显示可用的来源
本命令灵感及数据来自同名UNIX/Linux命令''')
  .build())


@fortune.handle()
async def handle_fortune(arg: Message = CommandArg()):
  fortunes = list_fortunes()
  filenames = arg.extract_plain_text().split()
  if not filenames:
    filename = random.choice(fortunes)
  else:
    filename = random.choice(filenames)
  if filename == "ls":
    await fortune.finish(" ".join(fortunes))
  elif filename not in fortunes:
    await fortune.finish(f"/usr/share/fortune/{filename} 不存在或不是Fortune文件")
  with open(f"/usr/share/fortune/{filename}.dat", "rb") as f:
    info = strfile.read_dat(f)
  with open(f"/usr/share/fortune/{filename}") as f:
    text = strfile.read_text(f, random.choice(info.offsets), info.delim)
  await fortune.finish(strip_033(text))
