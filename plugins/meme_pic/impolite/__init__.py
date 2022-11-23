from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
# RemapTransform((150, 150), ((0, 20), (154, 0), (164, 153), (22, 180)))  # noqa
OLD_SIZE = (150, 150)
NEW_SIZE = (164, 180)
TRANSFORM = (
  0.8955540939219657, -0.1231386879142573, 2.4627737582811897, 0.10983370584176559,
  0.8457195349815885, -16.91439069963202, -0.0004165322847504612, -0.0004034806049907501
)


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--text", "-t", default="你刚才说的话不是很礼貌！", metavar="文本", help=(
  "自定义文本，默认为“你刚才说的话不是很礼貌！”"
))
matcher = (
  command.CommandBuilder("meme_pic.impolite", "不文明", "不礼貌")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)

  def make() -> MessageSegment:
    target, _ = target_task.result()
    im = Image.open(DIR / "template.png")
    target = target.resize(OLD_SIZE, imutil.scale_resample())
    imutil.circle(target)
    target = target.transform(NEW_SIZE, Image.Transform.PERSPECTIVE, TRANSFORM, imutil.resample())
    im.paste(target, (137, 151), target)

    text_im = textutil.render(args.text, "serif", 50)
    text_im = imutil.contain_down(text_im, 471, 75)
    imutil.paste(im, text_im, (293, 80), anchor="mm")

    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
