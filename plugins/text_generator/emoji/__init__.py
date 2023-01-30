from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from util import command


def convert(src: str) -> str:
  from .data import emoji, pinyin
  i = 0
  count = len(src)
  result = ""
  while i < count:
    pinyin1 = pinyin.get(src[i], "")
    if i + 1 < len(src):
      pinyin2 = pinyin.get(src[i + 1], "")
      if pinyin1 + pinyin2 in emoji:
        result += emoji[pinyin1 + pinyin2]
        i += 2
        continue
    if pinyin1 in emoji:
      result += emoji[pinyin1]
    else:
      result += src[i]
    i += 1
  return result


emoji = (
  command.CommandBuilder("text_generator.emoji", "抽象话")
  .brief("🌶️💉💦🐮🍺")
  .usage("/抽象话 <文字>")
  .build()
)
@emoji.handle()
async def handle_ero(arg: Message = CommandArg()):
  if not arg:
    await emoji.finish(emoji.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text(convert(seg.data["text"])))
    else:
      output.append(seg)
  await emoji.finish(output)
