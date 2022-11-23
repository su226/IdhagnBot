from argparse import Namespace
from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
# RemapTransform((220, 160), ((0, 39), (225, 0), (236, 145), (25, 197)))  # noqa
OLD_SIZE = 220, 160
NEW_SIZE = 236, 197
TRANSFORM = (
  0.8469606952031231, -0.13401276822833844, 5.226497960904075, 0.15932974592085844,
  0.9192100726203283, -35.84919283219329, -0.0004890372852200551, -0.00027999415409538726
)


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接（可传入动图）"
))
parser.add_argument("--text", "-t", metavar="文本", default="来玩休闲游戏啊", help=(
  "自定义文本，默认为“来玩休闲游戏啊”"
))
group = parser.add_mutually_exclusive_group()
group.add_argument(
  "--webp", "-w", action="store_const", dest="format", const="webp", default="gif",
  help="使用WebP而非GIF格式（如果传入动图）"
)
group.add_argument(
  "--png", "--apng", "-p", action="store_const", dest="format", const="png",
  help="使用APNG而非GIF格式（如果传入动图）"
)
matcher = (
  command.CommandBuilder("meme_pic.laptop", "笔记本", "玩游戏")
  .category("meme_pic")
  .brief("[动]")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, raw=True)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    template = Image.open(DIR / "template.png")
    text_im = textutil.render(
      args.text, "sans", 40, color=(255, 255, 255), stroke=2, stroke_color=(0, 0, 0)
    )
    text_im = imutil.contain_down(text_im, template.width - 20, 100)
    imutil.paste(template, text_im, (template.width // 2, template.height - 20), anchor="mb")
    frames: List[Image.Image] = []
    for raw in imutil.frames(target):
      im = Image.new("RGB", template.size, (0, 0, 0))
      frame = ImageOps.pad(raw.convert("RGBA"), OLD_SIZE, imutil.scale_resample())
      frame = frame.transform(NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, imutil.resample())
      im.paste(frame, (162, 119), frame)
      im.paste(template, mask=template)
      frames.append(im)
    return imutil.to_segment(frames, target, afmt=args.format)

  await matcher.finish(await misc.to_thread(make))
