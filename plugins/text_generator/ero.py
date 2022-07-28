import random

import jieba.posseg as pseg
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from util import command

RATIO = 0.5


def convert(x, y):
  if random.random() > RATIO:
    return x
  if x in {"，", "。"}:
    return "……"
  if x in {"!", "！"}:
    return "❤"
  if len(x) > 1 and random.random() < 0.5:
    return f"{x[0]}……{x}"
  if y == "n" and random.random() < 0.5:
    x = "〇" * len(x)
  return f"……{x}"


ero = (
  command.CommandBuilder("text_generator.ero", "淫语")
  .brief("“较开放的漫画”会出现这个")
  .usage("/淫语 <文字>")
  .build())


@ero.handle()
async def handle_ero(arg: Message = CommandArg()):
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text("".join(
        convert(word, type) for word, type in pseg.cut(seg.data["text"]))))
    else:
      output.append(seg)
  await ero.finish(output)
