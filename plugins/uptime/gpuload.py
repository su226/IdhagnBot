import re
import sys

# 只适用于Linux+AMD，需要root权限
# 请使用PyInstaller、Nuitka等打包成原生程序后再使用
# nuitka3 gpuload.py
# sudo chown root gpuload.bin
# sudo chmod u+s gpuload.bin

with open("/sys/kernel/debug/dri/0/amdgpu_pm_info") as f:
  info = f.read()

print(sys.argv[1].format(
  clock = re.search(r"\d+(?= MHz \(SCLK\))", info)[0],
  memclock = re.search(r"\d+(?= MHz \(MCLK\))", info)[0],
  voltage = re.search(r"\d+(?= mV \(VDDGFX\))", info)[0],
  power = re.search(r"\d+\.\d+(?= W \(average GPU\))", info)[0],
  temp = re.search(r"(?<=GPU Temperature: )\d+", info)[0],
  load = re.search(r"(?<=GPU Load: )\d+", info)[0],
  memload = re.search(r"(?<=MEM Load: )\d+", info)[0]
))
