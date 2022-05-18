import os

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
import nonebot

from util import resources, command

PAGE = "file://" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
USAGE = "/5000兆元 <红色文本> [银色文本]"

choyen = (command.CommandBuilder("meme_text.5000choyen", "5000兆元", "兆元", "5000choyen", "choyen")
  .brief("生成想要5000兆元风格文字")
  .usage(USAGE)
  .build())
@choyen.handle()
async def handle_choyen(args: Message = CommandArg()):
  text = args.extract_plain_text().split()
  if len(text) == 2:
    top, bottom = text
  elif len(text) == 1:
    top = text[0]
    bottom = ""
  else:
    await choyen.finish(USAGE)
  browser = await resources.launch_pyppeteer()
  try:
    page = await browser.newPage()
    await page.goto(PAGE)
    top = top.replace("\\", "\\\\").replace("\"", "\\\"")
    bottom = bottom.replace("\\", "\\\\").replace("\"", "\\\"")
    img = await page.evaluate(f'draw("{top}", "{bottom}")')
    await choyen.finish(MessageSegment.image(img))
  finally:
    await browser.close()
