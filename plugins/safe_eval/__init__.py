from nonebot.params import CommandArg
import nonebot
from .lisp import parse, format, eval, math_env
from .safe_eval import safe_eval

usage = "/calc <数学表达式>\n“不保证”结果可靠"
calc = nonebot.on_command("calc")
calc.__cmd__ = "calc"
calc.__brief__ = "计算数学表达式"
calc.__doc__ = usage
@calc.handle()
async def handle_calc(args = CommandArg()):
  expr = str(args).rstrip()
  if expr == "":
    await calc.send(usage)
  else:
    await calc.send(expr + "\n=> ⑨")

lisp = nonebot.on_command("lisp")
lisp.__cmd__ = "lisp"
lisp.__brief__ = "计算Lisp风格的数学表达式"
@lisp.handle()
async def handle_lisp(args = CommandArg()):
  try:
    codes = parse(str(args))
  except Exception as e:
    await lisp.send(f"无效的Lisp: {e}")
    return
  segments = []
  env = math_env()
  for code in codes:
    segments.append(format(code))
    try:
      result = eval(code, env)
    except Exception as e:
      segments.append(f"=> 执行失败: {e}")
    else:
      result = "琪露诺" if result == 9 else str(result)
      segments.append(f"=> {result}")
  await lisp.send("\n".join(segments))

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
  code = str(args).rstrip()
  if not len(code):
    await python.finish(python.__doc__)
  killed, returncode, stdout, stderr = await safe_eval(code, TIMEOUT, NPROC, MEMORY, OUTPUT)
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
