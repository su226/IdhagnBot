import os
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, text, util

plugin_dir = os.path.dirname(os.path.abspath(__file__))

USAGE = "/鲁迅说 <文本>"
addict = (
  command.CommandBuilder("meme_text.luxun", "鲁迅说", "鲁迅")
  .brief("我没说过这句话")
  .usage(USAGE)
  .build())


@addict.handle()
async def handle_addict(args: Message = CommandArg()):
  content = args.extract_plain_text().rstrip()
  if not content:
    content = USAGE

  im = Image.open(os.path.join(plugin_dir, "template.jpg"))
  text_im = text.render(content, "sans", 38, color=(255, 255, 255), align="m", spacing=5)
  text_im = util.center(text_im, 440, 100)
  im.paste(text_im, (20, 300), text_im)
  text.paste(im, (320, 400), "——鲁迅", "sans", 30, color=(255, 255, 255))

  f = BytesIO()
  im.save(f, "png")
  await addict.send(MessageSegment.image(f))
