from dataclasses import dataclass
import subprocess as sp

@dataclass
class Info:
  unknown: bool
  model: str
  percent: int
  mem_percent: int
  clk: int
  temp: int

UEVENT_FILE = "uevent"

def read(card: str) -> Info:
  root = f"/sys/class/drm/{card}/device/"
  with open(root + UEVENT_FILE) as f:
    for i in f:
      if i.startswith("PCI_SLOT_NAME="):
        pci = i[14:-1]
        break
  proc = sp.run(["lspci", "-s", pci], capture_output=True, text=True)
  model = proc.stdout
  model = model[model.find(": ") + 2: -9]
  return Info(True, model, 0, 0, 0, 0)