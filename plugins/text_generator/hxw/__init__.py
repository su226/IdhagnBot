from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from util import command


def convert(src: str) -> str:
  from .data import hxw
  return "".join(hxw.get(x, x) for x in src)


hxw = (
  command.CommandBuilder("text_generator.hxw", "火星文")
  .brief("涐倒伱乜網丄沖蒗錒")
  .usage("/火星文 <文字>")
  .build()
)
@hxw.handle()
async def handle_ero(arg: Message = CommandArg()):
  if not arg:
    await hxw.finish(hxw.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text(convert(seg.data["text"])))
    else:
      output.append(seg)
  await hxw.finish(output)
