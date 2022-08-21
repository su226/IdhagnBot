import os
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageOps

from util import command, text, util

plugin_dir = os.path.dirname(os.path.abspath(__file__))

USAGE = "/成瘾 <文本>"
addict = (
  command.CommandBuilder("meme_text.addict", "成瘾前后", "成瘾")
  .brief("会露出笑容")
  .usage(USAGE)
  .build())


@addict.handle()
async def handle_addict(args: Message = CommandArg()):
  content = args.extract_plain_text().rstrip()
  if not content:
    await addict.finish(USAGE)
  im = Image.open(os.path.join(plugin_dir, "template.png"))
  text_im = text.render(content, "sans medium", 50, color=(255, 255, 255))
  text_im = util.center(text_im, 290, 72)
  im.paste(text_im, (398, 648), text_im)
  f = BytesIO()
  im.save(f, "png")
  await addict.send(MessageSegment.image(f))
