import random
from pathlib import Path
from typing import Dict, List, Literal, Tuple

from nonebot.adapters.onebot.v11 import MessageSegment
from playwright.async_api import async_playwright
from pydantic import BaseModel, parse_file_as

from util import command, misc

_dir = Path(__file__).resolve().parent
URL = (_dir / "index.html").as_uri()
DATA_FILE = _dir / "data.json"
del _dir
Continents = Literal["AF", "EU", "AS", "OA", "NA", "SA"]
CONTINENTS: Dict[Continents, str] = {
  "AF": "非洲",
  "EU": "欧洲",
  "AS": "亚洲",
  "OA": "大洋洲",
  "NA": "北美洲",
  "SA": "南美洲",
}

class Region(BaseModel):
  display_name: str
  name: str
  continent: Continents
  position: Tuple[float, float]
  weight: float


reborn = (
  command.CommandBuilder("reborn", "投胎")
  .brief("投胎模拟器")
  .build()
)
@reborn.handle()
async def handle_reborn() -> None:
  regions = parse_file_as(List[Region], DATA_FILE)
  region = random.choices(regions, [x.weight for x in regions])[0]
  msg = f"恭喜你投胎到了{CONTINENTS[region.continent]}的{region.display_name}"
  async with async_playwright() as p:
    browser = await misc.launch_playwright(p)
    page = await browser.new_page()
    await page.goto(URL)
    await page.evaluate("render", [list(region.position), region.name])
    data = await page.screenshot(full_page=True)
  await reborn.finish(msg + MessageSegment.image(data))
