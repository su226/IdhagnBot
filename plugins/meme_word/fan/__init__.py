from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


fan = (
  command.CommandBuilder("meme_word.fan", "狂粉", "狂爱")
  .category("meme_word")
  .usage("/狂粉 <文本>")
  .build()
)
@fan.handle()
async def handle_fan(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await fan.finish(fan.__doc__)

  def make() -> MessageSegment:
    im = Image.open(DIR / "template.jpg")
    text_im = textutil.render(text, "sans", 70, align="m")
    text_im = imutil.contain_down(text_im, 200, 120)
    imutil.paste(im, text_im, (244, 99), anchor="mm")
    return imutil.to_segment(im)

  await fan.finish(await misc.to_thread(make))
