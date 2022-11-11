from typing import cast

from mctools import PINGClient
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from pydantic import BaseModel, Field

from util import command, misc
from util.configs import SharedConfig


class Config(BaseModel):
  stat_address: str = ""
  ping_addresses: list[str] = Field(default_factory=list)


CONFIG = SharedConfig("minecraft", Config)


def parse_server(raw: str) -> tuple[str, int]:
  try:
    host, port = raw.rsplit(":", 1)
    return host, int(port)
  except ValueError:
    return raw, 25565


minecraft = (
  command.CommandBuilder("minecraft", "minecraft", "mc")
  .brief("查询Minecraft服务器的状态")
  .usage("如有异常会自动发送反馈")
  .rule(lambda: bool(CONFIG().stat_address))
  .help_condition(lambda _: bool(CONFIG().stat_address))
  .build())


@minecraft.handle()
async def handle_minecraft(bot: Bot):
  config = CONFIG()
  host, port = parse_server(config.stat_address)
  try:
    with PINGClient(host, port, format_method=PINGClient.REMOVE) as ping:
      stats = cast(dict, ping.get_stats())
  except Exception:
    for user in misc.superusers():
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
  for addr in config.ping_addresses:
    host, port = parse_server(addr)
    try:
      with PINGClient(host, port) as ping:
        segments.append(f"{addr} {round(ping.ping())}ms")
    except Exception:
      errors.append(addr)
      segments.append(f"{addr} 连接失败")
  if errors:
    for user in misc.superusers():
      await bot.send_private_msg(
        user_id=user, message="Minecraft服务器部分地址连接失败，请及时检修！\n" + "\n".join(errors))
    segments.append("部分地址连接失败，已经发送反馈")
  if "favicon" in stats:
    icon = stats["favicon"].removeprefix("data:image/png;base64,")
    await minecraft.finish(MessageSegment.image("base64://" + icon) + "\n".join(segments))
  await minecraft.finish("\n".join(segments))
