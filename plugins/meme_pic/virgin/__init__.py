from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--text", "-t", default="我说，那边的人全都是处男吗？", metavar="文本", help=(
  "自定义内容，默认为“我说，那边的人全都是处男吗？”"
))
matcher = (
  command.CommandBuilder("meme_pic.virgin", "处男")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    template = Image.open(DIR / "template.png")
    target = target.resize((370, 370), imutil.scale_resample())
    im = Image.new("RGB", (640, 480), (255, 255, 255))
    im.paste(target, mask=target)
    imutil.paste(im, template, im.size, anchor="rb")

    text_im = textutil.render(
      args.text, "sans", 32, color=(255, 255, 255), stroke=2, stroke_color=(0, 0, 0),
    )
    text_im = imutil.contain_down(text_im, 460, 50)
    imutil.paste(im, text_im, (im.width // 2, im.height - 35), anchor="mm")
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
