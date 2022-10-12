from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg

from util import command

from .safe_eval_js import safe_eval as eval_js
from .safe_eval_py import safe_eval as eval_py

TIMEOUT = 10
NPROC = 128
MEMORY = 128 * 1024 * 1024
OUTPUT = 1024
python = (
  command.CommandBuilder("safe_eval.python", "python")
  .brief("在沙箱中运行Python代码")
  .usage(f'''\
/python <代码>
代码可以换行，不会自动输出最后的结果
限制：
不能访问沙箱外文件
只能使用Python标准库
进程限制为 {NPROC} 个
时间限制为 {TIMEOUT} 秒
内存限制为 {MEMORY / 1024 / 1024} M
输出限制为 {OUTPUT} 字节''')
  .build())


@python.handle()
async def handle_python(args: Message = CommandArg()):
  code = args.extract_plain_text().rstrip()
  if not code:
    await python.finish(python.__doc__)
  killed, returncode, stdout, stderr = await eval_py(code, TIMEOUT, NPROC, MEMORY, OUTPUT)
  segments = []
  if killed:
    segments.append(f"退出代码：{returncode}（超时）")
  else:
    segments.append(f"退出代码：{returncode}")
  stdout = stdout.decode(errors='ignore')
  if not stdout:
    segments.append("标准输出：（空）")
  elif stdout.endswith("\n"):
    segments.append(f"标准输出：\n{stdout[:-1]}")
  else:
    segments.append(f"标准输出：（末尾没有换行）\n{stdout}")
  stderr = stderr.decode(errors='ignore')
  if not stderr:
    segments.append("标准错误：（空）")
  elif stderr.endswith("\n"):
    segments.append(f"标准错误：\n{stderr[:-1]}")
  else:
    segments.append(f"标准错误：（末尾没有换行）\n{stderr}")
  await python.finish("\n".join(segments))

JS_MEMORY = 512 * 1024 * 1024
js = (
  command.CommandBuilder("safe_eval.javascript", "javascript", "js", "node")
  .brief("在沙箱中运行NodeJS代码")
  .usage(f'''\
/node <代码>
代码可以换行，不会自动输出最后的结果
限制：
不能访问沙箱外文件
只能使用Node标准库
进程限制为 {NPROC} 个
时间限制为 {TIMEOUT} 秒
内存限制为 {JS_MEMORY / 1024 / 1024} M
输出限制为 {OUTPUT} 字节''')
  .build())


@js.handle()
async def handle_js(args: Message = CommandArg()):
  code = args.extract_plain_text().rstrip()
  if not code:
    await js.finish(js.__doc__)
  killed, returncode, stdout, stderr = await eval_js(code, TIMEOUT, NPROC, JS_MEMORY, OUTPUT)
  segments = []
  if killed:
    segments.append(f"退出代码：{returncode}（超时）")
  else:
    segments.append(f"退出代码：{returncode}")
  stdout = stdout.decode(errors='ignore')
  if not stdout:
    segments.append("标准输出：（空）")
  elif stdout.endswith("\n"):
    segments.append(f"标准输出：\n{stdout[:-1]}")
  else:
    segments.append(f"标准输出：（末尾没有换行）\n{stdout}")
  stderr = stderr.decode(errors='ignore')
  if not stderr:
    segments.append("标准错误：（空）")
  elif stderr.endswith("\n"):
    segments.append(f"标准错误：\n{stderr[:-1]}")
  else:
    segments.append(f"标准错误：（末尾没有换行）\n{stderr}")
  await js.finish("\n".join(segments))
