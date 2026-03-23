import math
import re
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Literal, Optional, cast

from aiohttp.web import BaseRequest, Response, Server, ServerRunner, TCPSite
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import ArgStr, CommandArg
from nonebot.typing import T_State
from playwright.async_api import async_playwright
from pydantic import BaseModel, PrivateAttr
from pyzim.archive import Zim
from pyzim.entry import ContentEntry
from pyzim.exceptions import EntryNotFound

from util import command, configs, misc


class Config(BaseModel):
  zim: str = ""
  page_size: int = 10
  width: int = 800
  scale: float = 1
  use_opencc: bool = True
  _archive: Optional[Zim] = PrivateAttr(None)

  @property
  def archive(self) -> Zim:
    if not self._archive:
      self._archive = Zim.open(self.zim)
    return self._archive


CONFIG = configs.SharedConfig("wikipedia", Config)
DIR = Path(__file__).resolve().parent
COMMON_SCRIPT_PATH = DIR / "common.js"
OPENCC_SCRIPT_PATH = DIR / "opencc.js"
CHARSET_RE = re.compile(r";\s*charset=([^;]*)")


def get_entry(archive: Zim, url: str) -> Optional[ContentEntry]:
  try:
    return cast(ContentEntry, archive.get_entry_by_full_url(url).resolve())
  except EntryNotFound:
    pass
  try:
    return cast(ContentEntry, archive.get_content_entry_by_url(url).resolve())
  except EntryNotFound:
    pass
  return None


async def handler(request: BaseRequest):
  def got_charset(match: re.Match[str]) -> str:
    nonlocal charset
    charset = match[1]
    return ""
  config = CONFIG()
  entry = get_entry(config.archive, request.path[1:])
  if not entry: 
    return Response(status=404, text="Not Found")
  charset = None
  # AIOHTTP要求charset是独立的参数……
  mime = CHARSET_RE.sub(got_charset, entry.mimetype)
  return Response(body=entry.read(), content_type=mime, charset=charset)


@asynccontextmanager
async def autostop(site: TCPSite) -> AsyncIterator[None]:
  await site.start()
  try:
    yield
  finally:
    await site.stop()


async def screenshot(
  path: str, format: Literal["png", "jpeg"] = "png", quality: Optional[int] = None,
) -> bytes:
  config = CONFIG()
  server = Server(handler)
  runner = ServerRunner(server)
  await runner.setup()
  with socket.socket() as s:
    s.bind(("", 0))
    port = s.getsockname()[1]
  site = TCPSite(runner, "localhost", port)
  async with autostop(site), async_playwright() as p:
    browser = await misc.launch_playwright(p)
    page = await browser.new_page(
      viewport={"width": config.width, "height": 1}, device_scale_factor=config.scale,
    )
    await page.goto(f"http://localhost:{port}/{path}")
    with open(COMMON_SCRIPT_PATH) as f:
      await page.evaluate(f.read())
    if config.use_opencc:
      with open(OPENCC_SCRIPT_PATH) as f:
        await page.evaluate(f.read())
    return await page.screenshot(full_page=True, type=format, quality=quality)


wikipedia = (
  command.CommandBuilder("wikipedia", "维基百科", "维基", "百科", "wikipedia", "wiki", "pedia")
  .rule(lambda: bool(CONFIG().zim))
  .help_condition(lambda _: bool(CONFIG().zim))
  .brief("搜索并查看离线维基百科")
  .usage("/维基百科 <搜索内容>")
  .build()
)
def format_choices(state: T_State) -> str:
  config = CONFIG()
  search = state["search"]
  count = state["count"]
  page = state["page"]
  begin = page * config.page_size
  segments = []
  for i, v in enumerate(search.iter_in_range(begin, config.page_size), begin + 1):
    segments.append(f"{i}: {v.title}")
  pages = math.ceil(count / config.page_size)
  segments.append(f"第 {page + 1} 页，共 {pages} 页，{count} 个结果")
  segments.append("- 发送数字查看页面")
  if begin + config.page_size < count:
    segments.append("- 发送“下”加载下一页")
  else:
    state["end"] = True
  segments.append("- 发送“退”退出")
  return "\n".join(segments)


@wikipedia.handle()
async def handle_wikipedia(state: T_State, msg: Message = CommandArg()) -> None:
  query = str(msg).rstrip()
  if not query:
    await wikipedia.finish(wikipedia.__doc__)
  config = CONFIG()
  state["search"] = search = config.archive.get_search().search(query)
  state["count"] = count = search.n_estimated
  state["page"] = 0
  state["end"] = False
  if count == 0:
    await wikipedia.finish("没有结果")
  await wikipedia.send(format_choices(state))

@wikipedia.got("choice")
async def got_choice(state: T_State, choice: str = ArgStr()) -> None:
  choice = choice.strip()
  if choice == "退":
    await wikipedia.finish("已退出")
  elif choice == "下":
    if state["end"]:
      await wikipedia.reject("没有下一页了，请重新输入，或发送“退”退出")
    state["page"] += 1
    await wikipedia.reject(format_choices(state))
  try:
    choice_int = int(choice)
  except ValueError:
    await wikipedia.reject("只能输入数字，请重新输入，或发送“退”退出")
  search = state["search"]
  count = state["count"]
  if choice_int < 1 or choice_int > count:
    await wikipedia.reject(f"只能发送 1 和 {count} 之间的数字，请重新输入，或发送“退”退出")
  path = next(iter(search.iter_in_range(choice_int - 1, 1))).full_url
  await wikipedia.finish(MessageSegment.image(await screenshot(path)))
