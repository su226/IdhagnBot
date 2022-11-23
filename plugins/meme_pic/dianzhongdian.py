from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter

parser = ArgumentParser(add_help=False)
parser.add_argument("line1", metavar="第一行", help="第一行文本")
parser.add_argument("line2", metavar="第二行", help="第二行文本，英文或日文请自行翻译")
parser.add_argument(
  "target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接"
)
matcher = (
  command.CommandBuilder("meme_pic.dianzhongdian", "典中典")
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
    target = target.convert("LA")
    target = imutil.resize_width(target, 500)
    line1_im = textutil.render(args.line1, "sans", 50, color=(255, 255, 255))
    line1_im = imutil.contain_down(line1_im, 500, 60)
    line2_im = textutil.render(args.line2, "sans", 25, color=(255, 255, 255))
    line2_im = imutil.contain_down(line2_im, 500, 35)

    im = Image.new("RGB", (500, target.height + 100))
    im.paste(target, mask=target.getchannel("A"))
    imutil.paste(im, line1_im, (target.width // 2, target.height + 30), anchor="mm")
    imutil.paste(im, line2_im, (target.width // 2, target.height + 78), anchor="mm")
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
