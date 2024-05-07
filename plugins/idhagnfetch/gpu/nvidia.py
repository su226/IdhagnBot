import subprocess as sp

from .common import Info

COMMAND = [
  "nvidia-smi",
  "--query-gpu=pci.bus_id,name,clocks.sm,temperature.gpu,utilization.gpu,utilization.memory",
  "--format=csv",
]
UEVENT_FILE = "uevent"


def read(card: str) -> Info:
  root = f"/sys/class/drm/{card}/device/"
  cur_pci = None
  with open(root + UEVENT_FILE) as f:
    for i in f:
      if i.startswith("PCI_SLOT_NAME="):
        cur_pci = i[14:]
        break
  if cur_pci is None:
    raise RuntimeError(f"无法获取PCI槽：{card}")
  proc = sp.run(COMMAND, capture_output=True, text=True)
  info = None
  for info in proc.stdout.splitlines()[1:]:
    pci, *info = info.split(", ")
    if pci[4:] == cur_pci:
      break
  if info is None:
    raise RuntimeError(f"无法获取状态：{card}")
  name, clk, temp, percent, mem_percent = info
  return Info(
    False, name, int(percent[:-2]), int(mem_percent[:-2]), int(clk[:-4]) * 1000000, int(temp))
