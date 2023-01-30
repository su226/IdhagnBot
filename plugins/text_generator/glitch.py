import random
from typing import Dict, List, Tuple, Union

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from util import command

DATA = {
  "up": [
    "\u0300", "\u0301", "\u0302", "\u0303", "\u0304", "\u0305", "\u0306", "\u0307", "\u0308",
    "\u0309", "\u030a", "\u030b", "\u030c", "\u030d", "\u030e", "\u030f", "\u0310", "\u0311",
    "\u0312", "\u0313", "\u0314", "\u031a", "\u033d", "\u033e", "\u033f", "\u0340", "\u0341",
    "\u0342", "\u0343", "\u0344", "\u0346", "\u034a", "\u034b", "\u034c", "\u0350", "\u0351",
    "\u0352", "\u0357", "\u035b"
  ],
  "mid": ["\u0334", "\u0335", "\u0336", "\u0337", "\u0338", "\u0488", "\u0489"],
  "down": [
    "\u0316", "\u0317", "\u0318", "\u0319", "\u031c", "\u031d", "\u031e", "\u031f", "\u0320",
    "\u0323", "\u0324", "\u0325", "\u0326", "\u0329", "\u032a", "\u032b", "\u032c", "\u032d",
    "\u032e", "\u032f", "\u0330", "\u0331", "\u0332", "\u0333", "\u0345", "\u0347", "\u0348",
    "\u0349", "\u034d", "\u034e", "\u0353", "\u0354", "\u0355", "\u0356", "\u0359", "\u035a"
  ],
  "under": ["\u0321", "\u0322", "\u0327", "\u0328", "\u035c", "\u0362"],
  "above": ["\u0315", "\u031b", "\u035d", "\u035e", "\u0360", "\u0361", "\u0487"]
}
PRESETS: List[Dict[str, Union[int, Tuple[int, int]]]] = [
  {"mid": 0, "above": 1, "under": 0, "up": (2, 5), "down": 0},
  {"mid": 0, "above": 1, "under": 0, "up": (4, 12), "down": 0},
  {"mid": 1, "above": 1, "under": 0, "up": (8, 16), "down": 0},
  {"mid": 0, "above": 0, "under": 1, "up": 0, "down": (2, 5)},
  {"mid": 0, "above": 0, "under": 1, "up": 0, "down": (4, 12)},
  {"mid": 1, "above": 0, "under": 1, "up": 0, "down": (8, 16)},
  {"mid": 1, "above": 0, "under": 0, "up": 0, "down": 0},
  {"mid": (1, 2), "above": 0, "under": 0, "up": 0, "down": 0},
  {"mid": 1, "above": 1, "under": 1, "up": 0, "down": 0},
  {"mid": 1, "above": 1, "under": 1, "up": (1, 3), "down": (1, 3)},
  {"mid": 1, "above": 1, "under": 1, "up": (2, 5), "down": (2, 5)},
  {"mid": 1, "above": 1, "under": 1, "up": (2, 8), "down": (2, 8)},
  {"mid": 0, "above": 0, "under": 0, "up": (4, 12), "down": (4, 12)},
  {"mid": 1, "above": 0, "under": 0, "up": (4, 12), "down": (4, 12)},
  {"mid": 0, "above": 0, "under": 0, "up": (4, 16), "down": (4, 16)},
  {"mid": 1, "above": 0, "under": 0, "up": (4, 16), "down": (4, 16)},
  {"mid": 0, "above": 0, "under": 0, "up": (8, 16), "down": (8, 16)},
  {"mid": 1, "above": 0, "under": 0, "up": (8, 16), "down": (8, 16)},
  {"mid": 0, "above": 0, "under": 0, "up": (12, 24), "down": (12, 24)},
  {"mid": 1, "above": 0, "under": 0, "up": (12, 24), "down": (12, 24)},
]


def convert(src: str, **kw: Union[int, Tuple[int, int]]) -> str:
  def convert_one(ch: str) -> str:
    result = ch
    for name, count in kw.items():
      if isinstance(count, tuple):
        count = random.randint(*count)
      chars = DATA[name]
      result += "".join(random.choice(chars) for _ in range(count))
    return result
  return "".join(x if x.isspace() else convert_one(x) for x in src)


glitch = (
  command.CommandBuilder("text_generator.glitch", "故障文")
  .usage("/故障文 <文字>")
  .build()
)
@glitch.handle()
async def handle_glitch(arg: Message = CommandArg()):
  if not arg:
    await glitch.finish(glitch.__doc__)
  output = Message()
  for seg in reversed(arg):
    if seg.type == "text":
      output.append(MessageSegment.text(convert(seg.data["text"], **PRESETS[11])))
    else:
      output.append(seg)
  await glitch.finish(output)
