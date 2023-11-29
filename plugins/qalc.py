import asyncio
import os

from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
from pydantic import BaseModel

from util import command, configs, misc


class Config(BaseModel):
  proxy: str = ""


CONFIG = configs.SharedConfig("qalc", Config)


qalc = (
  command.CommandBuilder("qalc", "qalc", "计算")
  .brief("强大的计算器")
  .usage('''\
/qalc <表达式>
基于Qalculate的，非常强大的计算器。

基本用法：
/qalc 16 - 9
16 - 9 = 7
带单位：
/qalc 16V * 9A
(16 × 伏) × (9 × 安) = 144 W
换算：
/qalc 25oC to oF
25 × 摄氏度 = 77 °F
汇率转换（自动更新）：
/qalc 100CNY to USD
100 × CNY ≈ $14.79230869''')
  .build()
)
@qalc.handle()
async def handle_qalc(arg: Message = CommandArg()):
  expr = str(arg).rstrip()
  if not expr:
    await qalc.finish(qalc.__doc__)
  read, write = os.pipe()
  proc = await asyncio.create_subprocess_exec(
    "qalc", expr, stdin=read, stdout=asyncio.subprocess.PIPE
  )
  os.write(write, b"n")
  os.close(write)
  await proc.wait()
  # qalc 在需要更新汇率的时候会询问 y/n，如果 n 被 qalc 吞掉了就说明需要更新汇率了
  if os.read(read, 1):
    result, _ = await proc.communicate()
  else:
    await qalc.send("正在更新汇率，请稍候……")
    config = CONFIG()
    proc = await asyncio.create_subprocess_exec(
      "qalc", "-exrates", expr, stdout=asyncio.subprocess.PIPE, env={"all_proxy": config.proxy}
    )
    result, _ = await proc.communicate()
    await proc.wait()
  await qalc.finish(misc.removesuffix(result.decode(), "\n"))
