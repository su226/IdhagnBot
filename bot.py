from pytz_deprecation_shim import PytzUsageWarning
from nonebot.adapters.onebot.v11 import Adapter
import nonebot
import warnings

warnings.simplefilter("ignore", PytzUsageWarning)

nonebot.init(_env_file="configs/nonebot.env", apscheduler_autostart=True)
nonebot.get_driver().register_adapter(Adapter)
nonebot.load_plugins("plugins")
nonebot.load_plugins("user_plugins")

from util.help import add_commands
add_commands()

if __name__ == "__main__":
  nonebot.run()
