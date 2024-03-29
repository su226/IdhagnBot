import pathlib
from typing import List, TypedDict
from urllib.parse import quote as encodeuri

import aiohttp
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field

from util import command, configs, misc


class Theme(TypedDict, total=False):
  foreground: str
  background: str
  cursor: str
  cursorAccent: str
  selectionBackground: str
  selectionForeground: str
  selectionInactiveBackground: str
  black: str
  red: str
  green: str
  yellow: str
  blue: str
  magenta: str
  cyan: str
  white: str
  brightBlack: str
  brightRed: str
  brightGreen: str
  brightYellow: str
  brightBlue: str
  brightMagenta: str
  brightCyan: str
  brightWhite: str
  extendedAnsi: List[str]


class Xterm(TypedDict, total=False):
  fontFamily: str
  theme: Theme


class Config(BaseModel):
  xterm: Xterm = Field(default_factory=Xterm)
  lang: str = "zh-cn"


CONFIG = configs.SharedConfig("wttrin", Config)
URL = (pathlib.Path(__file__).resolve().parent / "xterm.html").as_uri()

wttr = (
  command.CommandBuilder("wttrin", "wttrin", "wttr", "天气")
  .brief("可以在命令行看的天气")
  .usage('''\
/wttrin <城市>
城市名可以是中文，也可是是英文
天气数据来自 wttr.in，可以用 cURL 等工具在终端中查看，也可直接用浏览器打开
例如：curl https://wttr.in/北京
更多用法请参考 GitHub 上的 wttr.in 项目''')
  .build()
)
@wttr.handle()
async def handle_wttr(arg: Message = CommandArg()):
  city = arg.extract_plain_text().rstrip()
  if not city:
    await wttr.finish("但是我不知道你要查询哪里的天气诶……")
  config = CONFIG()
  async with aiohttp.ClientSession() as session:
    url = f"https://wttr.in/{encodeuri(city, '')}?lang={config.lang}"
    async with session.get(url) as response:
      content = await response.text()
  async with async_playwright() as p:
    browser = await misc.launch_playwright(p)
    page = await browser.new_page(viewport={"width": 1, "height": 1})
    await page.goto(URL)
    await page.evaluate("render", [content.rstrip(), config.xterm])
    data = await page.screenshot(full_page=True)
  await wttr.finish(MessageSegment.image(data))
