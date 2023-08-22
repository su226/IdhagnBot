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
parser.add_argument("--text", "-t", default="偷学群友数理基础", metavar="文本", help=(
  "自定义内容，默认为“偷学群友数理基础”"
))
matcher = (
  command.CommandBuilder("meme_pic.learn", "偷学")
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
    target = target.resize((1345, 1345), imutil.resample())
    im = Image.new("RGB", (2797, 1715), (213, 213, 213))
    template = Image.open(DIR / "template.png")
    im.paste(template, (100, 0))
    im.paste(target, (1352, 0), target)
    text_im = textutil.render(args.text, "sans bold", 240)
    text_im = imutil.contain_down(text_im, im.width - 200, 370)
    imutil.paste(im, text_im, (im.width // 2, 1530), anchor="mm")
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
