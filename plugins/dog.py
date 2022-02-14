from aiohttp import ClientSession
from nonebot.adapters.onebot.v11 import MessageSegment
import nonebot

CAT_API = "https://aws.random.cat/meow"
cat = nonebot.on_command("喵", aliases={"喵喵", "meow"})
cat.__cmd__ = ["喵", "喵喵", "meow"]
cat.__brief__ = "喵喵喵？喵喵。"
cat.__doc__ = "喵，喵喵。（翻译：API在国外，该命令缓慢是正常现象）"
@cat.handle()
async def handle_cat():
  try:
    async with ClientSession() as http:
      response = await http.get(CAT_API)
      data = await response.json()
      response = await http.get(data["file"])
      img = await response.read()
    if not img:
      raise Exception("Download failed")
  except:
    await cat.finish("网络错误")
  await cat.finish(MessageSegment.image(img))

DOG_API = "https://random.dog/woof.json"
dog = nonebot.on_command("汪", aliases={"汪汪", "woof"})
dog.__cmd__ = ["汪", "汪汪", "woof"]
dog.__brief__ = "汪？汪汪，汪汪汪！"
dog.__doc__ = "汪汪，汪汪。（翻译：API在国外，该命令缓慢是正常现象）"
@dog.handle()
async def handle_dog():
  try:
    async with ClientSession() as http:
      response = await http.get(DOG_API)
      data = await response.json()
      response = await http.get(data["url"])
      img = await response.read()
    if not img:
      raise Exception("Download failed")
  except:
    await cat.finish("网络错误")
  await cat.finish(MessageSegment.image(img))
