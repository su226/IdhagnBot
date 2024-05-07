from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from util.command import CommandBuilder

from . import rcnb

chinese = (
  CommandBuilder("text_generator.chinese.encode", "汉字乱码")
  .brief("鍙ゆ枃涔辩爜")
  .usage("/汉字乱码 <文字>")
  .build()
)
@chinese.handle()
async def handle_chinese(arg: Message = CommandArg()):
  if not arg:
    await chinese.finish(chinese.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text(seg.data["text"].encode("utf-8").decode("gbk", "replace")))
    else:
      output.append(seg)
  await chinese.finish(output)


blank = (
  CommandBuilder("text_generator.blank", "口口乱码")
  .brief("�ڿ�����")
  .usage("/口口乱码 <文字>\n根据设备不同，可能会显示为方形或问号")
  .build()
)
@blank.handle()
async def handle_blank(arg: Message = CommandArg()):
  if not arg:
    await blank.finish(blank.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text(seg.data["text"].encode("gbk").decode("utf-8", "replace")))
    else:
      output.append(seg)
  await blank.finish(output)


symbols = (
  CommandBuilder("text_generator.symbols.encode", "符号乱码")
  .brief("ç¬¦å·ä¹±ç")
  .usage("/符号乱码 <文字>")
  .build()
)
@symbols.handle()
async def handle_symbols(arg: Message = CommandArg()):
  if not arg:
    await symbols.finish(symbols.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text(seg.data["text"].encode("utf-8").decode("iso8859-1")))
    else:
      output.append(seg)
  await symbols.finish(output)


symbols_decode = (
  CommandBuilder("text_generator.symbols.decode", "还原符号乱码")
  .brief("ç¬¦å·ä¹±ç")
  .usage("/还原符号乱码 <符号乱码文字>")
  .build()
)
@symbols_decode.handle()
async def handle_symbols_decode(arg: Message = CommandArg()):
  if not arg:
    await symbols_decode.finish(symbols_decode.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      try:
        text = seg.data["text"].encode("iso8859-1").decode("utf-8")
      except ValueError:
        await symbols_decode.finish("还原失败")
      output.append(MessageSegment.text(text))
    else:
      output.append(seg)
  await symbols_decode.finish(output)


letters = (
  CommandBuilder("text_generator.letters.encode", "字母乱码")
  .brief("×ÖÄ¸ÂÒÂë")
  .usage("/字母乱码 <文字>")
  .build()
)
@letters.handle()
async def handle_letters(arg: Message = CommandArg()):
  if not arg:
    await letters.finish(letters.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text(seg.data["text"].encode("gbk").decode("iso8859-1")))
    else:
      output.append(seg)
  await letters.finish(output)


letters_decode = (
  CommandBuilder("text_generator.letters.decode", "还原字母乱码")
  .brief("×ÖÄ¸ÂÒÂë")
  .usage("/还原字母乱码 <字母乱码文字>")
  .build()
)
@letters_decode.handle()
async def handle_letters_decode(arg: Message = CommandArg()):
  if not arg:
    await letters_decode.finish(letters_decode.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      try:
        text = seg.data["text"].encode("iso8859-1").decode("gbk")
      except ValueError:
        await letters_decode.finish("还原失败")
      output.append(MessageSegment.text(text))
    else:
      output.append(seg)
  await letters_decode.finish(output)


question = (
  CommandBuilder("text_generator.question", "问号乱码")
  .brief("?号乱?")
  .usage("/问号乱码 <文字>")
  .build()
)
@question.handle()
async def handle_question(arg: Message = CommandArg()):
  if not arg:
    await question.finish(question.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text(
        seg.data["text"]
        .encode("utf-8")
        .decode("gbk", "replace")
        .encode("gbk", "replace")
        .decode("utf-8", "ignore"),
      ))
    else:
      output.append(seg)
  await question.finish(output)


kjk = (
  CommandBuilder("text_generator.kjk", "锟斤拷乱码", "锟斤拷")
  .brief("锟斤拷锟斤拷锟斤拷")
  .usage("/锟斤拷乱码 <文字>")
  .build()
)
@kjk.handle()
async def handle_kjk(arg: Message = CommandArg()):
  if not arg:
    await kjk.finish(kjk.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text(
        seg.data["text"]
        .encode("gbk")
        .decode("utf-8", "replace")
        .encode("utf-8")
        .decode("gbk", "replace"),
      ))
    else:
      output.append(seg)
  await kjk.finish(output)


rcnb_encode = (
  CommandBuilder("text_generator.rcnb.encode", "RCNB", "rcnb")
  .brief("ȐĉņþƦȻƝƃŔć")
  .usage("/字母乱码 <文字>")
  .build()
)
@rcnb_encode.handle()
async def handle_rcnb_encode(arg: Message = CommandArg()):
  if not arg:
    await rcnb_encode.finish(rcnb_encode.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      output.append(MessageSegment.text(rcnb.encode(seg.data["text"].encode())))
    else:
      output.append(seg)
  await rcnb_encode.finish(output)


rcnb_decode = (
  CommandBuilder("text_generator.rcnb.decode", "解码RCNB", "解码rcnb")
  .brief("ȐĉņþƦȻƝƃŔć")
  .usage("/解码RCNB <RCNB文字>")
  .build()
)
@rcnb_decode.handle()
async def handle_rcnb_decode(arg: Message = CommandArg()):
  if not arg:
    await rcnb_decode.finish(rcnb_decode.__doc__)
  output = Message()
  for seg in arg:
    if seg.type == "text":
      try:
        text = rcnb.decode(seg.data["text"].strip()).decode()
      except ValueError:
        await rcnb_decode.finish("解码失败")
      output.append(MessageSegment.text(text))
    else:
      output.append(seg)
  await rcnb_decode.finish(output)
