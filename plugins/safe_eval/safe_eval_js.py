import asyncio
import json
import os
import subprocess
from asyncio.streams import StreamReader, StreamWriter
from typing import Tuple, cast

from loguru import logger

env_dir = os.path.abspath("states/safe_eval_js")
if not os.path.exists(env_dir):
  logger.info("创建Node虚拟环境")
  os.makedirs("states/safe_eval_js", exist_ok=True)
  subprocess.run(["npm", "i", "posix"], cwd="states/safe_eval_js")

plugin_dir = os.path.dirname(os.path.abspath(__file__))


async def safe_eval(
  code: str, timeout: float, nproc: int, memory: int, output: int,
) -> Tuple[bool, int, bytes, bytes]:
  # TODO: 得有个办法自动获取这个
  proc = await asyncio.subprocess.create_subprocess_exec(
    "bwrap",
    "--unshare-all",
    "--clearenv",
    "--die-with-parent",
    "--ro-bind", "/lib64/ld-linux-x86-64.so.2", "/lib64/ld-linux-x86-64.so.2",
    "--ro-bind", "/usr/lib/libnode.so.111", "/usr/lib/libnode.so.111",
    "--ro-bind", "/usr/lib/libz.so.1", "/usr/lib/libz.so.1",
    "--ro-bind", "/usr/lib/libuv.so.1", "/usr/lib/libuv.so.1",
    "--ro-bind", "/usr/lib/libbrotlidec.so.1", "/usr/lib/libbrotlidec.so.1",
    "--ro-bind", "/usr/lib/libbrotlienc.so.1", "/usr/lib/libbrotlienc.so.1",
    "--ro-bind", "/usr/lib/libcares.so.2", "/usr/lib/libcares.so.2",
    "--ro-bind", "/usr/lib/libnghttp2.so.14", "/usr/lib/libnghttp2.so.14",
    "--ro-bind", "/usr/lib/libcrypto.so.3", "/usr/lib/libcrypto.so.3",
    "--ro-bind", "/usr/lib/libssl.so.3", "/usr/lib/libssl.so.3",
    "--ro-bind", "/usr/lib/libicui18n.so.72", "/usr/lib/libicui18n.so.72",
    "--ro-bind", "/usr/lib/libicuuc.so.72", "/usr/lib/libicuuc.so.72",
    "--ro-bind", "/usr/lib/libstdc++.so.6", "/usr/lib/libstdc++.so.6",
    "--ro-bind", "/usr/lib/libm.so.6", "/usr/lib/libm.so.6",
    "--ro-bind", "/usr/lib/libgcc_s.so.1", "/usr/lib/libgcc_s.so.1",
    "--ro-bind", "/usr/lib/libc.so.6", "/usr/lib/libc.so.6",
    "--ro-bind", "/usr/lib/libdl.so.2", "/usr/lib/libdl.so.2",
    "--ro-bind", "/usr/lib/libpthread.so.0", "/usr/lib/libpthread.so.0",
    "--ro-bind", "/usr/lib/libbrotlicommon.so.1", "/usr/lib/libbrotlicommon.so.1",
    "--ro-bind", "/usr/lib/libicudata.so.72", "/usr/lib/libicudata.so.72",
    "--ro-bind", "/usr/bin/node", "/usr/bin/node",
    "--ro-bind", "states/safe_eval_js/node_modules", "/node_modules",
    "--ro-bind", os.path.join(plugin_dir, "do_eval.js"), "/do_eval.js",
    "node", "do_eval.js",
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
