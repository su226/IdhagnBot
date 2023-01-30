import random

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from util import command


def convert(src: str, ratio: float = 0.5) -> str:
  def convert_one(word: str, flag: str) -> str:
    if random.random() > ratio:
      return word
    if word in {"，", "。"}:
      return "……"
    if word in {"!", "！"}:
      return "❤"
    if len(word) > 1 and random.random() < 0.5:
      return f"{word[0]}……{word}"
    if flag == "n" and random.random() < 0.5:
      word = "〇" * len(word)
    return f"……{word}"
  import jieba.posseg as pseg
  return "".join(convert_one(word, flag) for word, flag in pseg.cut(src))


ero = (
  command.CommandBuilder("text_generator.ero", "淫语")
  .brief("“较开放的漫画”会出现这个")
  .usage("/淫语 <文字>")
  .build()
)
@ero.handle()
async def handle_ero(arg: Message = CommandArg()):
  if not arg:
    await ero.finish(ero.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text(convert(seg.data["text"])))
    else:
      output.append(seg)
  await ero.finish(output)
