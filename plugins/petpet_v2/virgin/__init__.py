import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, text, util

from ..util import get_image_and_user

DIR = Path(__file__).resolve().parent

parser = ArgumentParser(add_help=False)
parser.add_argument(
  "target", nargs="?", default="", metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接"
)
parser.add_argument(
  "--text", "-t", default="我说，那边的人全都是处男吗？", metavar="文本",
  help="默认为“我说，那边的人全都是处男吗？”"
)

matcher = command.CommandBuilder("petpet_v2.virgin", "处男") \
  .category("petpet_v2") \
  .shell(parser) \
  .auto_reject() \
  .build()
@matcher.handle()
async def handler(
  bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()
) -> None:
  try:
    target, _ = await get_image_and_user(bot, event, args.target, event.self_id)
  except util.AggregateError as e:
    await matcher.finish("\n".join(e))

  def make() -> MessageSegment:
    nonlocal target
    template = Image.open(DIR / "template.png")
    target = target.resize((370, 370), util.scale_resample)
    im = Image.new("RGB", (640, 480), (255, 255, 255))
    im.paste(target, mask=target)
    util.paste(im, template, im.size, anchor="rb")

    text_im = text.render(
      args.text, "sans", 32, color=(255, 255, 255), stroke=2, stroke_color=(0, 0, 0)
    )
    text_im = util.contain_down(text_im, 460, 50)
    util.paste(im, text_im, (im.width // 2, im.height - 35), anchor="mm")
    return util.pil_image(im)

  await matcher.finish(await asyncio.to_thread(make))
