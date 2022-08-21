import asyncio

from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg

from util import command


USAGE = '''\
/qalc <表达式>
基于Qalculator的，非常强大的计算器。

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
100 × CNY ≈ $14.79230869'''
qalc = (
  command.CommandBuilder("qalc", "qalc", "计算")
  .brief("强大的计算器")
  .usage(USAGE)
  .build())


@qalc.handle()
async def handle_qalc(arg: Message = CommandArg()):
  expr = str(arg).rstrip()
  if not expr:
    await qalc.finish(USAGE)
  proc = await asyncio.create_subprocess_exec(
    "qalc", expr, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
  result, _ = await proc.communicate(b"y")  # 更新汇率
  if proc.returncode is None:
    proc.terminate()
  await qalc.finish(result.decode().removesuffix("\n"))
