from typing import cast

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from util import command

_data = {
  # 字母
  'a': 'ɐ', 'b': 'q', 'c': 'ɔ', 'd': 'p', 'e': 'ǝ', 'f': 'ɟ', 'g': 'ƃ', 'h': 'ɥ', 'i': 'ᴉ',
  'j': 'ɾ', 'k': 'ʞ', 'l': 'l', 'm': 'ɯ', 'n': 'u', 'o': 'o', 'p': 'd', 'q': 'b', 'r': 'ɹ',
  's': 's', 't': 'ʇ', 'u': 'n', 'v': 'ʌ', 'w': 'ʍ', 'x': 'x', 'y': 'ʎ', 'z': 'z',
  'A': '∀', 'B': '𐐒', 'C': 'Ɔ', 'D': 'ᗡ', 'E': 'Ǝ', 'F': 'Ⅎ', 'G': '⅁', 'H': 'H', 'I': 'I',
  'J': 'ſ', 'K': '⋊', 'L': '˥', 'M': 'W', 'N': 'ᴎ', 'O': 'O', 'P': 'Ԁ', 'Q': 'Ό', 'R': 'ᴚ',
  'S': '5', 'T': '┴', 'U': '∩', 'V': 'Λ', 'W': 'M', 'X': 'X', 'Y': '⅄', 'Z': 'Z',
  # 数字
  '1': '⇂', '2': '↊', '3': 'Ɛ', '4': 'ᔭ', '5': 'S', '6': '9', '7': '𝘓', '8': '8', '9': '6',
  '0': '0',
  '１': '⇂', '２': '↊', '３': 'Ɛ', '４': 'ᔭ', '５': 'S', '６': '９', '７': '𝘓', '８': '８',
  '９': '６', '０': '０',
  # 括号
  '(': ')', '[': ']', '{': '}', '<': '>', '〈': '〉', '❪': '❫', '❬': '❭', '❰': '❱', '❲': '❳',
  '❴': '❵', '⟦': '⟧', '⟨': '⟩', '⟮': '⟯', '⦃': '⦄', '⦅': '⦆', '⦗': '⦘', '⧼': '⧽', '⸨': '⸩',
  '❮': '❯', '⟪': '⟫', '⦇': '⦈', '⦉': '⦊', '⌈': '⌋', '⌊': '⌉', '「': '」', '『': '』',
  '〈': '〉', '【': '】', '《': '》', '〔': '〕', '〖': '〗', '〚': '〛', '⁽': '₎', '⁾': '₍',
  '﹙': '﹚', '﹛': '﹜', '﹝': '﹞', '⏜': '⏝', '⏞': '⏟', '⎴': '⎵', '⏠': '⏡', '︵': '︶',
  '︗': '︘', '︷': '︸', '︹': '︺', '︿': '﹀', '﹁': '﹂', '﹇': '﹈', '︻': '︼', '︽': '︾',
  '﹃': '﹄',
  # 其他特殊符号
  '?': '¿', '!': '¡', '.': '˙', ',': '‘', ';': '؛', '&': '⅋', '_': '‾', '/': '\\', '∴': '∵',
}
DATA = {v: k for k, v in _data.items()}
DATA.update(_data)
del _data
DATA = {k: v for k, v in DATA.items() if k != v}


upside_down = (
  command.CommandBuilder("text_generator.upside_down", "颠倒")
  .brief("上下颠倒文字")
  .usage('''\
/颠倒 <文字>
仅支持英文大小写和数字，中文只反转顺序''')
  .build()
)
@upside_down.handle()
async def handle_upside_down(arg: Message = CommandArg()):
  if not arg:
    await upside_down.finish(upside_down.__doc__)
  output = Message()
  for seg in reversed(arg):
    if seg.type == "text":
      text = "".join(DATA.get(i, i) for i in reversed(cast(str, seg.data["text"])))
      output.append(MessageSegment.text(text))
    else:
      output.append(seg)
  await upside_down.finish(output)
