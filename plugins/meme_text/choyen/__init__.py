from util import resources
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
import nonebot
import os

PAGE = "file://" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

choyen = nonebot.on_command("5000兆元", aliases={"兆元", "5000choyen", "choyen"})
choyen.__cmd__ = ["5000兆元", "兆元", "5000choyen", "choyen"]
choyen.__brief__ = "生成想要5000兆元风格文字"
choyen.__doc__ = "/5000兆元 <红色文本> <银色文本>"
@choyen.handle()
async def handle_choyen(args: Message = CommandArg()):
  text = args.extract_plain_text().split()
  if len(text) > 2:
    await choyen.finish("请输入最多两段空格分割的文字")
  elif len(text) == 2:
    top, bottom = text
  else:
    top = text[0]
    bottom = ""
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
