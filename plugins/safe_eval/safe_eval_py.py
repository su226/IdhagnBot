from typing import cast
from asyncio.streams import StreamReader, StreamWriter
import asyncio
import os
import pickle
import venv

from nonebot.log import logger

plugin_dir = os.path.dirname(os.path.abspath(__file__))
# env_dir = os.path.abspath("states/safe_eval_env")
# if not os.path.exists(env_dir):
#   logger.info("创建Python虚拟环境")
#   venv.create(env_dir)

async def safe_eval(code: str, timeout: float, nproc: int, memory: int, output: int) -> tuple[bool, int, bytes, bytes]:
  proc = await asyncio.subprocess.create_subprocess_exec("bwrap",
    "--unshare-all",
    "--clearenv",
    "--die-with-parent",
    "--ro-bind", "/lib64/ld-linux-x86-64.so.2", "/lib64/ld-linux-x86-64.so.2",
    "--ro-bind", "/usr/bin/python", "/usr/bin/python",
    "--ro-bind", "/usr/lib/python3.10", "/usr/lib/python3.10",
    "--ro-bind", "/usr/lib/libm.so.6", "/usr/lib/libm.so.6",
    "--ro-bind", "/usr/lib/libutil.so.1", "/usr/lib/libutil.so.1",
    "--ro-bind", "/usr/lib/libdl.so.2", "/usr/lib/libdl.so.2",
    "--ro-bind", "/usr/lib/libpthread.so.0", "/usr/lib/libpthread.so.0",
    "--ro-bind", "/usr/lib/libc.so.6", "/usr/lib/libc.so.6",
    "--ro-bind", "/usr/lib/libpython3.10.so.1.0", "/usr/lib/libpython3.10.so.1.0",
    "--ro-bind", os.path.join(plugin_dir, "do_eval.py"), "/do_eval.py",
    "python", "do_eval.py",
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )
  stdin = cast(StreamWriter, proc.stdin)
  stdin.write(pickle.dumps({
    "code": code,
    "nproc": nproc,
    "memory": memory,
  }))
  stdin.write_eof()
  killed = False
  try:
    await asyncio.wait_for(proc.wait(), timeout)
  except asyncio.TimeoutError:
    proc.kill()
    killed = True
  returncode = await proc.wait()
  stdout = await cast(StreamReader, proc.stdout).read(output)
  stderr = await cast(StreamReader, proc.stderr).read(output)
  return (killed, returncode, stdout, stderr)
