from util import misc

from .common import Item

API = "https://api.bilibili.com/x/web-interface/popular?ps=50&pn={}"


async def get_data() -> list[Item]:
  result = []
  http = misc.http()
  pn = 1
  while True:
    async with http.get(API.format(pn)) as response:
      data = await response.json()
    for i in data["data"]["list"]:
      result.append(Item(
        url=i["short_link"],
        title=i["title"],
        image=i["pic"],
        content=i["rcmd_reason"]["content"] + "|" + i["desc"]
      ))
    if data["data"]["no_more"]:
      break
    pn += 1
  return result
