from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


not_call_me = (
  command.CommandBuilder("meme_word.not_call_me", "不喊我")
  .category("meme_word")
  .brief("开impart不喊我是吧")
  .usage("/不喊我 <文本>")
  .build()
)
@not_call_me.handle()
async def handle_not_call_me(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await not_call_me.finish(not_call_me.__doc__)

  def make() -> MessageSegment:
    text_im = textutil.render(text, "sans", 40, box=170, align="m")
    text_im = imutil.contain_down(text_im, 115, 155)
    im = Image.open(DIR / "template.png")
    imutil.paste(im, text_im, (283, 87), anchor="mm")
    return imutil.to_segment(im)

  await not_call_me.finish(await misc.to_thread(make))
