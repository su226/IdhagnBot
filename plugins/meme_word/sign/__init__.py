from pathlib import Path

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent
# RemapTransform((360, 260), ((33, 0), (375, 120), (333, 387), (0, 258)))  # noqa: ERA001
OLD_SIZE = (360, 260)
NEW_SIZE = (375, 387)
TRANSFORM = (
  1.0593407468579847, 0.1354970722725227, -34.958244646312494, -0.33301607844333025,
  0.9490958235634742, 10.989530588631391, 0.00015720582795168063, -6.17732100774087e-05,
)


sign = (
  command.CommandBuilder("meme_word.sign", "举牌")
  .category("meme_word")
  .usage("/举牌 <文本>")
  .build()
)
@sign.handle()
async def handle_sign(args: Message = CommandArg()):
  text = args.extract_plain_text().rstrip()
  if not text:
    await sign.finish(sign.__doc__)

  def make() -> MessageSegment:
    im = Image.open(DIR / "template.jpg")
    text_im = textutil.render(text, "sans", 80, color=(81, 32, 27), box=540, align="m")
    text_im = imutil.center_pad(text_im, *OLD_SIZE)
    text_im = text_im.transform(
      NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, imutil.resample(),
    )
    im.paste(text_im, (285, 24), text_im)
    return imutil.to_segment(im)

  await sign.finish(await misc.to_thread(make))
