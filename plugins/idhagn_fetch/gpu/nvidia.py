from .common import Info
import subprocess as sp

COMMAND = [
  "nvidia-smi",
  "--query-gpu=pci.bus_id,name,clocks.sm,temperature.gpu,utilization.gpu,utilization.memory",
  "--format=csv"
]
UEVENT_FILE = "uevent"

@staticmethod
def read(card: str) -> Info:
  root = f"/sys/class/drm/{card}/device/"
  with open(root + UEVENT_FILE) as f:
    for i in f:
      if i.startswith("PCI_SLOT_NAME="):
        cur_pci = i[14:]
        break
  proc = sp.run(COMMAND, capture_output=True, text=True)
  for info in proc.stdout.splitlines()[1:]:
    pci, name, clk, temp, percent, mem_percent = info.split(", ")
    if pci[4:] == cur_pci:
      break
  return Info(False, name, int(percent[:-2]), int(mem_percent[:-2]), int(clk[:-4]) * 1000000, int(temp))
