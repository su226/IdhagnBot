from nonebot.params import CommandArg
import nonebot
from .safe_eval_py import safe_eval as safe_eval_py
from .safe_eval_js import safe_eval as safe_eval_js

TIMEOUT = 10
NPROC = 128
MEMORY = 128 * 1024 * 1024
OUTPUT = 1024
python = nonebot.on_command("python")
python.__cmd__ = "python"
python.__brief__ = "在沙箱中运行Python代码"
python.__doc__ = f'''\
/python <代码>
代码可以换行，不会自动输出最后的结果
限制：
不能访问沙箱外文件
只能使用Python标准库
进程限制为 {NPROC} 个
时间限制为 {TIMEOUT} 秒
内存限制为 {MEMORY / 1024 / 1024} M
输出限制为 {OUTPUT} 字节'''
@python.handle()
async def handle_python(args = CommandArg()):
  code = args.extract_plain_text().rstrip()
  if not len(code):
    await python.finish(python.__doc__)
  killed, returncode, stdout, stderr = await safe_eval_py(code, TIMEOUT, NPROC, MEMORY, OUTPUT)
  segments = []
  if killed:
    segments.append(f"退出代码：{returncode}（超时）")
  else:
    segments.append(f"退出代码：{returncode}")
  stdout = stdout.decode(errors='ignore')
  if not len(stdout):
    segments.append(f"标准输出：（空）")
  elif stdout.endswith("\n"):
    segments.append(f"标准输出：\n{stdout[:-1]}")
  else:
    segments.append(f"标准输出：（末尾没有换行）\n{stdout}")
  stderr = stderr.decode(errors='ignore')
  if not len(stderr):
    segments.append(f"标准错误：（空）")
  elif stderr.endswith("\n"):
    segments.append(f"标准错误：\n{stderr[:-1]}")
  else:
    segments.append(f"标准错误：（末尾没有换行）\n{stderr}")
  await python.finish("\n".join(segments))

JS_MEMORY = 512 * 1024 * 1024
js = nonebot.on_command("js", aliases={"node"})
js.__cmd__ = ["js", "node"]
js.__brief__ = "在沙箱中运行NodeJS代码"
js.__doc__ = f'''\
/node <代码>
代码可以换行，不会自动输出最后的结果
限制：
不能访问沙箱外文件
只能使用Node标准库
进程限制为 {NPROC} 个
时间限制为 {TIMEOUT} 秒
内存限制为 {JS_MEMORY / 1024 / 1024} M
输出限制为 {OUTPUT} 字节'''
@js.handle()
async def handle_js(args = CommandArg()):
  code = args.extract_plain_text().rstrip()
  if not len(code):
    await js.finish(js.__doc__)
  killed, returncode, stdout, stderr = await safe_eval_js(code, TIMEOUT, NPROC, JS_MEMORY, OUTPUT)
  segments = []
  if killed:
    segments.append(f"退出代码：{returncode}（超时）")
  else:
    segments.append(f"退出代码：{returncode}")
  stdout = stdout.decode(errors='ignore')
  if not len(stdout):
    segments.append(f"标准输出：（空）")
  elif stdout.endswith("\n"):
    segments.append(f"标准输出：\n{stdout[:-1]}")
  else:
    segments.append(f"标准输出：（末尾没有换行）\n{stdout}")
  stderr = stderr.decode(errors='ignore')
  if not len(stderr):
    segments.append(f"标准错误：（空）")
  elif stderr.endswith("\n"):
    segments.append(f"标准错误：\n{stderr[:-1]}")
  else:
    segments.append(f"标准错误：（末尾没有换行）\n{stderr}")
  await js.finish("\n".join(segments))
