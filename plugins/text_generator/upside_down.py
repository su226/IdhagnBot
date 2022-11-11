from nonebot.adapters import Message
from nonebot.params import CommandArg

from util import command

MAP = {
  'a': 'ɐ', 'b': 'q', 'c': 'ɔ', 'd': 'p', 'e': 'ǝ', 'f': 'ɟ', 'g': 'ƃ', 'h': 'ɥ', 'i': 'ᴉ',
  'j': 'ɾ', 'k': 'ʞ', 'l': 'l', 'm': 'ɯ', 'n': 'u', 'o': 'o', 'p': 'd', 'q': 'b', 'r': 'ɹ',
  's': 's', 't': 'ʇ', 'u': 'n', 'v': 'ʌ', 'w': 'ʍ', 'x': 'x', 'y': 'ʎ', 'z': 'z',
  'A': '∀', 'B': '𐐒', 'C': 'Ɔ', 'D': 'ᗡ', 'E': 'Ǝ', 'F': 'Ⅎ', 'G': '⅁', 'H': 'H', 'I': 'I',
  'J': 'ſ', 'K': '⋊', 'L': '˥', 'M': 'W', 'N': 'ᴎ', 'O': 'O', 'P': 'Ԁ', 'Q': 'Ό', 'R': 'ᴚ',
  'S': 'S', 'T': '┴', 'U': '∩', 'V': 'Λ', 'W': 'M', 'X': 'X', 'Y': '⅄', 'Z': 'Z',
  '1': '⇂', '2': '↊', '3': 'Ɛ', '4': 'ᔭ', '5': 'S', '6': '9', '7': '𝘓', '8': '8', '9': '6',
  '0': '0',
  '?': '¿', '!': '¡', '.': '˙', ',': '‘', '&': '⅋', '_': '‾', '/': '\\',
  '(': ')', ')': '(', '[': ']', ']': '[', '{': '}', '}': '{', '<': '>', '<': '>'
}
MAP.update({v: k for k, v in MAP.items()})


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
  text = arg.extract_plain_text()
  result = "".join(MAP.get(i, i) for i in reversed(text))
  await upside_down.finish(result)
