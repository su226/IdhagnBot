import os
import re
import subprocess as sp

from .common import Info

PERCENT_FILE = "gpu_busy_percent"
MEM_PERCENT_FILE = "mem_busy_percent"
CLK_FILE = "freq1_input"
MEM_CLK_FILE = "freq2_input"
TEMP_FILE = "temp1_input"
JUNCTION_TEMP_FILE = "temp2_input"
MEM_TEMP_FILE = "temp3_input"
VDD_FILE = "in0_input"
UEVENT_FILE = "uevent"


def read(card: str) -> Info:
  root = f"/sys/class/drm/{card}/device/"
  pci = None
  with open(root + UEVENT_FILE) as f:
    for i in f:
      if i.startswith("PCI_SLOT_NAME="):
        pci = i[14:-1]
        break
  if pci is None:
    raise RuntimeError(f"无法获取PCI槽：{card}")
  proc = sp.run(["lspci", "-s", pci], capture_output=True, text=True)
  model = proc.stdout
  model = model[model.rfind("[") + 1:model.rfind("]")]
  model = model.replace("OEM", "")
  model = re.sub(r"\s*/\s*", "/", model)
  hwmon = root + "hwmon/" + os.listdir(root + "hwmon")[0] + "/"
  with open(root + PERCENT_FILE) as f:
    percent = int(f.read())
  with open(root + MEM_PERCENT_FILE) as f:
    mem_percent = int(f.read())
  with open(hwmon + CLK_FILE) as f:
    clk = int(f.read())
  with open(hwmon + TEMP_FILE) as f:
    temp = int(f.read()) // 1000
  return Info(False, "AMD/ATI " + model, percent, mem_percent, clk, temp)
