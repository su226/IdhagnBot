from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


meteor = (
  command.CommandBuilder("meme_word.meteor", "流星")
  .category("meme_word")
  .usage("/流星 <文本>")
  .build()
)
@meteor.handle()
async def handle_not_call_me(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await meteor.finish(meteor.__doc__)

  def make() -> MessageSegment:
    text_im = textutil.render(text, "sans", 80, color=(255, 255, 255), box=1125, align="m")
    text_im = imutil.contain_down(text_im, 750, 210)
    im = Image.open(DIR / "template.png")
    imutil.paste(im, text_im, (580, 235), anchor="mm")
    return imutil.to_segment(im)

  await meteor.finish(await misc.to_thread(make))
