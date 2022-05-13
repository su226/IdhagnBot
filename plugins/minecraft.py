from pydantic import Field
from mctools import PINGClient
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
import nonebot

from util.config import BaseConfig

class Config(BaseConfig):
  __file__ = "minecraft"
  local_address: str = "127.0.0.1"
  extern_addresses: list[str] = Field(default_factory=list)

CONFIG = Config.load()

def parse_server(raw: str) -> tuple[str, int]:
  try:
    host, port = raw.rsplit(":", 1)
    return host, int(port)
  except ValueError:
    return raw, 25565


minecraft = nonebot.on_command("minecraft", aliases={"mc"})
minecraft.__cmd__ = ["minecraft", "mc"]
minecraft.__brief__ = "查询Minecraft服务器的状态"
minecraft.__doc__ = "如有异常会自动发送反馈"
@minecraft.handle()
async def handle_minecraft(bot: Bot):
  driver = nonebot.get_driver()
  host, port = parse_server(CONFIG.local_address)
  try:
    with PINGClient(host, port, format_method=PINGClient.REMOVE) as ping:
      stats = ping.get_stats()
  except:
    for user in driver.config.superusers:
      await bot.send_private_msg(user_id=user, message="Minecraft服务器异常，请及时检修！")
    await minecraft.finish("服务器连接失败，已经发送反馈")
  segments = []
  segments.append(stats["description"])
  segments.append(f"版本：{stats['version']['name']}")
  online = stats['players']['online']
  limit = stats['players']['max']
  players = '、'.join(x[0] for x in stats['players'].get('sample', []))
  segments.append(f"{online}/{limit}名玩家：{players}")
  segments.append("地址：")
  errors = []
  for addr in CONFIG.extern_addresses:
    host, port = parse_server(addr)
    try:
      with PINGClient(host, port) as ping:
        segments.append(f"{addr} {round(ping.ping())}ms")
    except:
      errors.append(addr)
      segments.append(f"{addr} 连接失败")
  if errors:
    for user in driver.config.superusers:
      await bot.send_private_msg(user_id=user, message="Minecraft服务器部分地址连接失败，请及时检修！\n" + "\n".join(errors))
    segments.append("部分地址连接失败，已经发送反馈")
  await minecraft.finish(MessageSegment.image("base64://" + stats['favicon'].removeprefix("data:image/png;base64,")) + MessageSegment.text("\n".join(segments)))
