from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


meteor2 = (
  command.CommandBuilder("meme_word.meteor2", "流星2")
  .category("meme_word")
  .usage("/流星2 <文本>")
  .build()
)
@meteor2.handle()
async def handle_not_call_me(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await meteor2.finish(meteor2.__doc__)

  def make() -> MessageSegment:
    text_im = textutil.render(text, "sans", 50, box=375, align="m")
    text_im = imutil.contain_down(text_im, 250, 80)
    im = Image.open(DIR / "template.png")
    imutil.paste(im, text_im, (191, 342), anchor="mm")
    return imutil.to_segment(im)

  await meteor2.finish(await misc.to_thread(make))
