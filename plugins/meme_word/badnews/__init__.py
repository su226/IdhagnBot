from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


badnews = (
  command.CommandBuilder("meme_word.badnews", "悲报")
  .category("meme_word")
  .usage("/悲报 <文本>")
  .build()
)
@badnews.handle()
async def handle_goodnews(args: Message = CommandArg()):
  def make() -> MessageSegment:
    content = args.extract_plain_text().rstrip() or badnews.__doc__ or ""
    im = Image.open(DIR / "template.png")
    text_im = textutil.render(
      content, "sans", 60, box=im.width * 2, stroke=4, stroke_color=(255, 255, 255), align="m",
    )
    text_im = imutil.contain_down(text_im, 480, 250)
    imutil.paste(im, text_im, (im.width // 2, 220), anchor="mm")
    return imutil.to_segment(im)
  await badnews.finish(await misc.to_thread(make))
