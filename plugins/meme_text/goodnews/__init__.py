import os
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, text, util

plugin_dir = os.path.dirname(os.path.abspath(__file__))

USAGE = "/喜报 <文本>"
goodnews = (
  command.CommandBuilder("meme_text.goodnews", "喜报")
  .brief("NullPointerException")
  .usage(USAGE)
  .build())


@goodnews.handle()
async def handle_goodnews(args: Message = CommandArg()):
  content = args.extract_plain_text().rstrip() or USAGE
  im = Image.open(os.path.join(plugin_dir, "template.jpg"))
  text_im = text.render(
    content, "sans", 80, color=(238, 0, 0), stroke=6, stroke_color=(255, 255, 153), align="m")
  text_im = util.center(text_im, 480, 250)
  im.paste(text_im, ((im.width - text_im.width) // 2, (im.height - text_im.height) // 2), text_im)
  f = BytesIO()
  im.save(f, "png")
  await goodnews.send(MessageSegment.image(f))
