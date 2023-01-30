from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from util import command

ant = (
  command.CommandBuilder("text_generator.ant", "蚂蚁文", "菊花文")
  .brief("也\u0489叫\u0489菊\u0489花\u0489文\u0489")
  .usage("/蚂蚁文 <文字>")
  .build()
)
@ant.handle()
async def handle_ant(arg: Message = CommandArg()):
  if not arg:
    await ant.finish(ant.__doc__)
  output = Message()
  for seg in reversed(arg):
    if seg.type == "text":
      text = "".join(i + "\u0489" for i in seg.data["text"])
      output.append(MessageSegment.text(text))
    else:
      output.append(seg)
  await ant.finish(output)
