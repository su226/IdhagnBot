import asyncio
import json
import os
import sys
from asyncio.streams import StreamReader, StreamWriter
from typing import Tuple, cast

plugin_dir = os.path.dirname(os.path.abspath(__file__))


async def safe_eval(
  code: str, timeout: float, nproc: int, memory: int, output: int,
) -> Tuple[bool, int, bytes, bytes]:
  version = f"{sys.version_info.major}.{sys.version_info.minor}"
  proc = await asyncio.subprocess.create_subprocess_exec(
    "bwrap",
    "--unshare-all",
    "--clearenv",
    "--die-with-parent",
    "--ro-bind", "/lib64/ld-linux-x86-64.so.2", "/lib64/ld-linux-x86-64.so.2",
    "--ro-bind", "/usr/bin/python", "/usr/bin/python",
    "--ro-bind", f"/usr/lib/python{version}", f"/usr/lib/python{version}",
    "--tmpfs", f"/usr/lib/python{version}/site-packages",
    "--ro-bind", "/usr/lib/libm.so.6", "/usr/lib/libm.so.6",
    "--ro-bind", "/usr/lib/libc.so.6", "/usr/lib/libc.so.6",
    "--ro-bind", f"/usr/lib/libpython{version}.so.1.0", f"/usr/lib/libpython{version}.so.1.0",
    "--ro-bind", os.path.join(plugin_dir, "do_eval.py"), "/do_eval.py",
    "python", "do_eval.py",
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )
  stdin = cast(StreamWriter, proc.stdin)
  stdin.write(json.dumps({
    "code": code,
    "nproc": nproc,
    "memory": memory,
  }).encode())
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
