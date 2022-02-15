# IdhagnBot
一个以娱乐功能为主的QQ机器人，基于Nonebot2开发

*本项目以[我的兽设](https://su226.tk/2021/07/24/my-fursona/)命名*

## 功能
详见[我的博客](https://su226.tk/2022/01/12/idhagn-bot/)

提示：部分功能，如沙箱执行Python，需安装第三方软件

## 安装
本项目使用Python 3.10.2开发，不保证兼容旧版Python
```shell
git clone https://github.com/su226/IdhagnBot.git
cd IdhagnBot
python3 -m venv env
. env/bin/activate
pip install -r requirements.txt
```

## 使用
你需要先安装一个OneBot V11（原CQHTTP）实现，并且选择一个NoneBot2[驱动器](https://v2.nonebot.dev/docs/start/install-driver)，这里以[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)和AIOHTTP（正向WebSocket连接）为例。（AIOHTTP也作为部分插件的HTTP库使用，因此使用其他适配器也必须安装）

可参照Nonebot2的文档：
* https://v2.nonebot.dev/docs/tutorial/choose-driver#aiohttp
* https://adapter-onebot.netlify.app/docs/guide/setup/#正向-websocket-连接

需要注意的是Nonebot2的配置文件在configs/nonebot.env，而非默认的.env
```dotenv
DRIVER=~aiohttp
ONEBOT_WS_URLS=["ws://127.0.0.1:6700"] # 端口号要与go-cqhttp一致
SUPERUSERS=["1234567890"] # 超管用户，替换成你的QQ号
```

本项目不使用nb-cli，因此配置完成后直接使用`python3 bot.py`运行机器人即可

## 项目结构
```
IdhagnBot
|- 📁 configs (gitignore)配置目录
  |- 📄 nonebot.env Nonebot2配置
  |- 📄 *.yaml 插件配置（如果对应插件没有配置，会在日志中提示）
|- 📁 core_plugins 核心插件，提供权限管理、帮助文档等功能，是其他插件的依赖
|- 📁 env (gitignore)Python虚拟环境
|- 📁 plugins 其他插件及其所需的资源
|- 📁 resources (gitignore)用户自定义资源
|- 📁 states (gitignore)状态文件，用于记录缓存、统计数据等（不建议手动编辑）
|- 📁 user_plugins (gitignore)用户插件，可以根据自己的需要拓展机器人功能
|- 📁 util 插件之间共用的代码（TODO：将core_plugins中的功能挪到util）
|- 📄 .gitignore
|- 📄 bot.py 机器人主程序
|- 📄 requirements.txt
|- 📄 README.md
|- 📄 LICENSE
```

## 特别感谢
* [Nonebot2](https://v2.nonebot.dev/)
* [go-cqhttp](https://docs.go-cqhttp.org/)
* [人生重开模拟器](https://github.com/VickScarlet/lifeRestart)
* 部分资源来自[nonebot-plugin-petpet](https://github.com/MeetWq/nonebot-plugin-petpet)
* [emojimix](https://tikolu.net/emojimix/)
* 以及其他参考过的Nonebot2插件
