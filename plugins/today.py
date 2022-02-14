from aiohttp import ClientSession
import nonebot

today = nonebot.on_command("今天", aliases={"today"})
today.__cmd__ = ["今天", "today"]
today.__brief__ = "查看历史上的今天"
@today.handle()
async def handle_today():
  async with ClientSession() as http:
    response = await http.get("https://www.ipip5.com/today/api.php?type=json")
    data = await response.json()
  result = [f"今天是{data['result'][-1]['year']}年{data['today']}，历史上的今天是："]
  for i in data["result"][:-1]:
    result.append(f"{i['year']}: {i['title']}")
  await today.finish("\n".join(result))
