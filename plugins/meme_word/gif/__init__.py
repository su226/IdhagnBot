import shlex
from pathlib import Path
from typing import List, Tuple

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image
from typing_extensions import LiteralString as LStr

from util import command, imutil, misc, textutil

DIR = Path(__file__).resolve().parent


def register(id: LStr, name: LStr, subtitles: List[Tuple[int, int, LStr]]) -> None:
  examples = "\n".join(x[2] for x in subtitles)
  matcher_t = (
    command.CommandBuilder(f"meme_word.gif.{id}", name)
    .category("meme_word")
    .usage(f'''\
/{name} - 查看示例
/{name} {" ".join(f"<文本{i}>" for i in range(1, len(subtitles) + 1))} - 制作梗图
示例内容：
{examples}''')
    .build()
  )

  async def handler(args: Message = CommandArg()):
    try:
      argv = shlex.split(args.extract_plain_text())
    except ValueError as e:
      await matcher_t.finish(str(e))
    if argv and len(argv) != len(subtitles):
      await matcher_t.finish(matcher_t.__doc__)

    def make() -> MessageSegment:
      im = Image.open(DIR / f"{id}.gif")
      i = 0
      frames: List[Image.Image] = []
      for j, raw in enumerate(imutil.frames(im)):
        begin, end, example = subtitles[i]
        if begin < j < end:
          frame = raw.convert("RGB")
          text = argv[i] if argv else example
          text_im = textutil.render(
            text, "sans", 20, color=(255, 255, 255), stroke=1, stroke_color=(0, 0, 0)
          )
          text_im = imutil.contain_down(text_im, im.width - 10, im.height - 10)
          imutil.paste(frame, text_im, (im.width // 2, im.height - 5), anchor="mb")
          frames.append(frame)
          if j + 1 >= end and i + 1 < len(subtitles):
            i += 1
        else:
          frames.append(raw.copy())
      return imutil.to_segment(frames, im)

    await matcher_t.finish(await misc.to_thread(make))
  matcher_t.handle()(handler)


register("chanshenzi", "馋身子", [
  (0, 16, "你那叫喜欢吗？"),
  (16, 31, "你那是馋她身子"),
  (33, 40, "你下贱！"),
])
register("nihaosaoa", "你好骚啊", [
  (0, 14, "既然追求刺激"),
  (16, 26, "就贯彻到底了"),
  (42, 61, "你好骚啊"),
])
register("qiegewala", "窃格瓦拉", [
  (0, 15, "没有钱啊 肯定要做的啊"),
  (16, 31, "不做的话没有钱用"),
  (31, 38, "那你不会去打工啊"),
  (38, 48, "有手有脚的"),
  (49, 68, "打工是不可能打工的"),
  (68, 86, "这辈子不可能打工的"),
])
register("shishilani", "食屎啦你", [
  (14, 21, "穿西装打领带"),
  (23, 36, "拿大哥大有什么用"),
  (38, 46, "跟着这样的大哥"),
  (60, 66, "食屎啦你"),
])
register("shuifandui", "谁反对", [
  (3, 14, "我话说完了"),
  (21, 26, "谁赞成"),
  (31, 38, "谁反对"),
  (40, 45, "我反对"),
])
register("wangjingze", "王境泽", [
  (0, 9, "我就是饿死"),
  (12, 24, "死外边 从这里跳下去"),
  (25, 35, "不会吃你们一点东西"),
  (37, 48, "真香"),
])
register("weisuoyuwei", "为所欲为", [
  (11, 14, "好啊"),
  (27, 38, "就算你是一流工程师"),
  (42, 61, "就算你出报告再完美"),
  (63, 81, "我叫你改报告你就要改"),
  (82, 95, "毕竟我是客户"),
  (96, 105, "客户了不起啊"),
  (111, 131, "Sorry 客户真的了不起"),
  (145, 157, "以后叫他天天改报告"),
  (157, 167, "天天改 天天改"),
])
register("wunian", "五年怎么过的", [
  (11, 20, "五年"),
  (35, 50, "你知道我这五年是怎么过的吗"),
  (59, 77, "我每天躲在家里玩贪玩蓝月"),
  (82, 95, "你知道有多好玩吗"),
])
register("yalidaye", "压力大爷", [
  (0, 16, "外界都说我们压力大"),
  (21, 47, "我觉得吧压力也没有那么大"),
  (52, 77, "主要是28岁了还没媳妇儿"),
])
register("zengxiaoxian", "曾小贤", [
  (3, 15, "平时你打电子游戏吗"),
  (24, 30, "偶尔"),
  (30, 46, "星际还是魔兽"),
  (56, 63, "连连看"),
])
