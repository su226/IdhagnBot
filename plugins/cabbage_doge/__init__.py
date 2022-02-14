from io import BytesIO
from PIL import Image, ImageOps
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.params import CommandArg
import os
import nonebot
import random

plugin_dir = os.path.dirname(os.path.abspath(__file__))
IMAGES = 50
DURATION = 100
CSS_COLORS = {
  "black": "000000",
  "silver": "c0c0c0",
  "gray": "808080",
  "white": "ffffff",
  "maroon": "800000",
  "red": "ff0000",
  "purple": "800080",
  "fuchsia": "ff00ff",
  "green": "008000",
  "lime": "00ff00",
  "olive": "808000",
  "yellow": "ffff00",
  "navy": "000080",
  "blue": "0000ff",
  "teal": "008080",
  "aqua": "00ffff",
  "orange": "ffa500",
  "aliceblue": "f0f8ff",
  "antiquewhite": "faebd7",
  "aquamarine": "7fffd4",
  "azure": "f0ffff",
  "beige": "f5f5dc",
  "bisque": "ffe4c4",
  "blanchedalmond": "ffebcd",
  "blueviolet": "8a2be2",
  "brown": "a52a2a",
  "burlywood": "deb887",
  "cadetblue": "5f9ea0",
  "chartreuse": "7fff00",
  "chocolate": "d2691e",
  "coral": "ff7f50",
  "cornflowerblue": "6495ed",
  "cornsilk": "fff8dc",
  "crimson": "dc143c",
  "cyan": "00ffff",
  "darkblue": "00008b",
  "darkcyan": "008b8b",
  "darkgoldenrod": "b8860b",
  "darkgray": "a9a9a9",
  "darkgreen": "006400",
  "darkgrey": "a9a9a9",
  "darkkhaki": "bdb76b",
  "darkmagenta": "8b008b",
  "darkolivegreen": "556b2f",
  "darkorange": "ff8c00",
  "darkorchid": "9932cc",
  "darkred": "8b0000",
  "darksalmon": "e9967a",
  "darkseagreen": "8fbc8f",
  "darkslateblue": "483d8b",
  "darkslategray": "2f4f4f",
  "darkslategrey": "2f4f4f",
  "darkturquoise": "00ced1",
  "darkviolet": "9400d3",
  "deeppink": "ff1493",
  "deepskyblue": "00bfff",
  "dimgray": "696969",
  "dimgrey": "696969",
  "dodgerblue": "1e90ff",
  "firebrick": "b22222",
  "floralwhite": "fffaf0",
  "forestgreen": "228b22",
  "gainsboro": "dcdcdc",
  "ghostwhite": "f8f8ff",
  "gold": "ffd700",
  "goldenrod": "daa520",
  "greenyellow": "adff2f",
  "grey": "808080",
  "honeydew": "f0fff0",
  "hotpink": "ff69b4",
  "indianred": "cd5c5c",
  "indigo": "4b0082",
  "ivory": "fffff0",
  "khaki": "f0e68c",
  "lavender": "e6e6fa",
  "lavenderblush": "fff0f5",
  "lawngreen": "7cfc00",
  "lemonchiffon": "fffacd",
  "lightblue": "add8e6",
  "lightcoral": "f08080",
  "lightcyan": "e0ffff",
  "lightgoldenrodyellow": "fafad2",
  "lightgray": "d3d3d3",
  "lightgreen": "90ee90",
  "lightgrey": "d3d3d3",
  "lightpink": "ffb6c1",
  "lightsalmon": "ffa07a",
  "lightseagreen": "20b2aa",
  "lightskyblue": "87cefa",
  "lightslategray": "778899",
  "lightslategrey": "778899",
  "lightsteelblue": "b0c4de",
  "lightyellow": "ffffe0",
  "limegreen": "32cd32",
  "linen": "faf0e6",
  "magenta": "ff00ff",
  "mediumaquamarine": "66cdaa",
  "mediumblue": "0000cd",
  "mediumorchid": "ba55d3",
  "mediumpurple": "9370db",
  "mediumseagreen": "3cb371",
  "mediumslateblue": "7b68ee",
  "mediumspringgreen": "00fa9a",
  "mediumturquoise": "48d1cc",
  "mediumvioletred": "c71585",
  "midnightblue": "191970",
  "mintcream": "f5fffa",
  "mistyrose": "ffe4e1",
  "moccasin": "ffe4b5",
  "navajowhite": "ffdead",
  "oldlace": "fdf5e6",
  "olivedrab": "6b8e23",
  "orangered": "ff4500",
  "orchid": "da70d6",
  "palegoldenrod": "eee8aa",
  "palegreen": "98fb98",
  "paleturquoise": "afeeee",
  "palevioletred": "db7093",
  "papayawhip": "ffefd5",
  "peachpuff": "ffdab9",
  "peru": "cd853f",
  "pink": "ffc0cb",
  "plum": "dda0dd",
  "powderblue": "b0e0e6",
  "rosybrown": "bc8f8f",
  "royalblue": "4169e1",
  "saddlebrown": "8b4513",
  "salmon": "fa8072",
  "sandybrown": "f4a460",
  "seagreen": "2e8b57",
  "seashell": "fff5ee",
  "sienna": "a0522d",
  "skyblue": "87ceeb",
  "slateblue": "6a5acd",
  "slategray": "708090",
  "slategrey": "708090",
  "snow": "fffafa",
  "springgreen": "00ff7f",
  "steelblue": "4682b4",
  "tan": "d2b48c",
  "thistle": "d8bfd8",
  "tomato": "ff6347",
  "turquoise": "40e0d0",
  "violet": "ee82ee",
  "wheat": "f5deb3",
  "whitesmoke": "f5f5f5",
  "yellowgreen": "9acd32",
  "rebeccapurple": "663399",
}

Color = tuple[int, int, int]

def parse_color(color: str) -> Color:
  color = color.lower().removeprefix("#")
  if color in CSS_COLORS:
    color = CSS_COLORS[color]
  if len(color) != 6:
    raise ValueError("color string len != 6")
  color = int(color, 16)
  return (color >> 16, (color >> 8) & 0xff, color & 0xff)

def blend(color1: Color, color2: Color, r: float) -> Color:
  r2 = 1 - r
  return (int(color1[0] * r + color2[0] * r2), int(color1[1] * r + color2[1] * r2), int(color1[2] * r + color2[2] * r2))

cabbage = nonebot.on_command("菜狗")
cabbage.__cmd__ = "菜狗"
cabbage.__brief__ = "生成彩色菜狗GIF"
cabbage.__doc__ = '''\
/菜狗 - 生成随机颜色的菜狗
/菜狗 <颜色> - 生成指定颜色的菜狗
/菜狗 <多个颜色> - 生成渐变色的菜狗
颜色可以是16进制，也可以是CSS颜色'''
@cabbage.handle()
async def handle_cabbage(args = CommandArg()):
  try:
    colors = list(map(parse_color, str(args).split()))
  except:
    await cabbage.finish("无效的颜色")
  if len(colors) == 0:
    colors = [parse_color(random.choice(list(CSS_COLORS.values())))]
  frames: list[Image.Image] = []
  for i in range(IMAGES):
    index = i / (IMAGES - 1.0) * (len(colors) - 1)
    ratio = index % 1
    index = int(index)
    if ratio < 1e-2:
      color = colors[index]
    else:
      color = blend(colors[index + 1], colors[index], ratio)
    im = Image.open(os.path.join(plugin_dir, f"{i}.png"))
    im = ImageOps.colorize(im, (0, 0, 0), (255, 255, 255), color)
    frames.append(im)
  f = BytesIO()
  frames[0].save(f, "gif", append_images=frames[1:], save_all=True, duration=DURATION, loop=0)
  await cabbage.send(MessageSegment.image(f))
