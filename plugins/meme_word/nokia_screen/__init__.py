from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageOps

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


nokia_screen = (
  command.CommandBuilder("meme_word.nokia_screen", "诺基亚屏幕")
  .category("meme_word")
  .brief("有内鬼，终止交易")
  .usage('''\
/诺基亚屏幕 <文本>
自动换行，文本不能超过 7 行''')
  .build()
)
@nokia_screen.handle()
async def handle_nokia(args: Message = CommandArg()):
  def make() -> MessageSegment:
    text = misc.removeprefix(args.extract_plain_text().rstrip(), ".") or nokia_screen.__doc__ or ""
    font = textutil.special_font("pixel", "sans")
    layout = textutil.layout(text, font, 64, box=710)
    if layout.get_pixel_size()[1] > 450:
      layout = textutil.layout("文本不能超过 7 行", font, 32, box=710)
    text_im = textutil.render(layout)
    text_im = ImageOps.expand(text_im, (0, 0, 710 - text_im.width, 450 - text_im.height))
    text_im = text_im.rotate(-9.3, imutil.resample(), True)
    header_im = textutil.render(f"{len(text)}/900", font, 64, color=(129, 212, 250))
    header_im = header_im.rotate(-9.3, imutil.resample(), True)
    im = Image.open(DIR / "template.jpg")
    im.paste(text_im, (207, 320), text_im)
    imutil.paste(im, header_im, (1010, 419), anchor="rb")
    return imutil.to_segment(im)
  await nokia_screen.finish(await misc.to_thread(make))
