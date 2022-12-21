from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


slap = (
  command.CommandBuilder("meme_word.slap", "一巴掌")
  .category("meme_word")
  .usage("/一巴掌 <文本>")
  .build()
)
@slap.handle()
async def handle_slap(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await slap.finish(slap.__doc__)

  def make() -> MessageSegment:
    template = Image.open(DIR / "template.png")
    text_im = textutil.render(text, "sans", 80, box=template.width * 2, align="m")
    size = (max(template.width, text_im.width + 20), 12 + template.height + text_im.height)
    im = Image.new("RGB", size, (255, 255, 255))
    imutil.paste(im, template, (im.width // 2, 12), anchor="mt")
    imutil.paste(im, text_im, (im.width // 2, template.height + 12), anchor="mt")
    return imutil.to_segment(im)

  await slap.finish(await misc.to_thread(make))
