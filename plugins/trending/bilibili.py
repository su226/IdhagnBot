from typing import List

from util import misc
from util.api_common import bilibili_auth

from .common import Item

API = "https://api.bilibili.com/x/web-interface/popular?ps=50&pn={}"


async def get_data() -> List[Item]:
  result = []
  http = misc.http()
  pn = 1
  while True:
    async with http.get(API.format(pn), headers={"User-Agent": misc.BROWSER_UA}) as response:
      data = bilibili_auth.ApiError.check(await response.json())
    for i in data["list"]:
      result.append(Item(
        url=i["short_link_v2"],
        title=i["title"],
        image=i["pic"],
        content=i["rcmd_reason"]["content"] + "|" + i["desc"],
      ))
    if data["no_more"]:
      break
    pn += 1
  return result
