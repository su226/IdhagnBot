import asyncio
import itertools
from argparse import Namespace
from pathlib import Path
from typing import Awaitable, Optional, Tuple

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
BRACKETS = [  # 所有形式的大括号、中括号、小括号、尖括号，来自中州韵输入法（）
  "{}", "『』", "〖〗", "｛｝", "[]", "「」", "【】", "〔〕", "［］", "〚〛", "〘〙", "()", "（）",
  "<>", "《》", "〈〉", "«»", "‹›", "⟨⟩"
]


parser = ArgumentParser(add_help=False)
parser.add_argument(
  "targets", nargs="*", default=["<急>"], metavar="目标",
  help="可使用@、QQ号、昵称、群名片或图片链接，或者用括号包起来的字符（最多10个）"
)
parser.add_argument(
  "--text", "-t", default="我是急急国王", metavar="文本",
  help="默认为“我是急急国王”"
)
parser.add_argument(
  "--source", "-s", default="", metavar="源",
  help="可使用@、QQ号、昵称、群名片或图片链接，或者用括号包起来的字符"
)
matcher = (
  command.CommandBuilder("meme_pic.jiji_king", "急急国王")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  def get_image(
    g: AvatarGetter, pattern: str, default: int, size: int, prompt: str
  ) -> "asyncio.Task[Image.Image]":
    for left, right in BRACKETS:
      if pattern.startswith(left) and pattern.endswith(right):
        return g.submit(misc.to_thread(make_char, pattern[1:-1], size))
    return g.submit(get_avatar(g.get(pattern, default, prompt), size))

  async def get_avatar(
    task: Awaitable[Tuple[Image.Image, Optional[int]]], size: int
  ) -> Image.Image:
    avatar, _ = await task
    return await misc.to_thread(avatar.resize, (size, size), imutil.scale_resample())

  def make_char(char: str, size: int) -> Image.Image:
    fg = textutil.render(char, "sans bold", size * 0.67, color=(255, 255, 255))
    fg = ImageOps.pad(fg, (size, size), imutil.resample())
    im = Image.new("RGB", fg.size)
    im.paste(fg, mask=fg)
    return im

  if len(args.targets) > 10:
    await matcher.finish("最多只能有 10 个目标")
  async with AvatarGetter(bot, event) as g:
    target_tasks = [
      get_image(g, pattern, event.self_id, 90, f"目标{i}")
      for i, pattern in enumerate(args.targets, 1)
    ]
    source_task = get_image(g, args.source, event.user_id, 125, "源")

  def make() -> MessageSegment:
    targets = [task.result() for task in target_tasks]
    source = source_task.result()
    block_count = max(5, len(targets))
    im = Image.new("RGB", (10 + block_count * 100, 400), (255, 255, 255))
    template = Image.open(DIR / "template.png")
    x = (im.width - template.width) // 2
    imutil.paste(im, template, (x, 6))
    imutil.paste(im, source, (x + 237, 5))

    repeat = [block_count // len(targets)] * len(targets)
    for i in range(block_count % len(targets)):
      repeat[i] += 1
    blocks = list(itertools.chain.from_iterable(
      [im] * count for im, count in zip(targets, repeat)
    ))

    for i, block in enumerate(blocks):
      im.paste(block, (10 + i * 100, 200))

    text_im = textutil.render(args.text, "sans bold", 60)
    text_im = imutil.contain_down(text_im, im.width - 10, 90)
    imutil.paste(im, text_im, (im.width // 2, 345), anchor="mm")

    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
