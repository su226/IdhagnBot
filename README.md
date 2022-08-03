# 🐱 IdhagnBot 🤖
一个以娱乐功能为主的QQ机器人，基于Nonebot2开发

*本项目以[我的兽设](https://su226.tk/2021/07/24/my-fursona/)命名，主要服务我自己的[闲聊群](https://qm.qq.com/cgi-bin/qm/qr?k=USDC9Yc0PPxBHHIVp5KIoHYSmuBHJK2u)*

## 功能
详见[我的博客](https://su226.tk/2022/01/12/idhagn-bot/)

部分功能需安装第三方软件：
* 离线维基百科：libzim（注意这个是GPL协议）
* 沙箱执行Python：bubblewrap（虽然这个也是GPL，但是是subprocess调用的）
* 沙箱执行JavaScript: bubblewrap、nodejs、npm
* MC服务器状态：mctools
* IdhagnFetch（仿[neofetch](https://github.com/dylanaraps/neofetch)的状态信息）：psutil
  * 注：显卡信息直接从`/sys/class/drm`读取，因此只支持Linux
* text_generator.ero（顾名思义）：jieba
* ~~petpet_v2的部分功能：numpy、opencv-python~~ 暂未实装
* 配置文件使用PyYAML解析，安装libyaml以使用C语言解析器（否则将使用纯Python解析器）
* 部分功能需要pyppeteer，默认为空字符串（也就是让pyppeteer自动下载），可修改配置文件为其他路径

## 安装
本项目使用Linux + Python 3.10开发，未在Windows或MacOS上测试过，且不兼容旧版Python
```shell
# 以ArchLinux为例，请自行换成你的发行版的包管理器
sudo pacman -S cairo pango gobject-introspection
git clone https://github.com/su226/IdhagnBot.git
cd IdhagnBot
# 只安装基础功能
pdm install
# 或者安装全部功能
sudo pacman -S libyaml bubblewrap nodejs npm
pdm install -G all
```

## 使用
你需要先安装一个OneBot V11（原CQHTTP）实现，并且选择一个NoneBot2[驱动器](https://v2.nonebot.dev/docs/start/install-driver)，这里以[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)和AIOHTTP（正向WebSocket连接）为例。（AIOHTTP也作为部分插件的HTTP库使用，因此使用其他适配器也必须安装）

可参照Nonebot2的文档：
* https://v2.nonebot.dev/docs/tutorial/choose-driver#aiohttp
* https://adapter-onebot.netlify.app/docs/guide/setup/#正向-websocket-连接

推荐使用configs/bot.yaml而非.env配置Nonebot2
```yaml
nonebot:
  driver: ~aiohttp
  onebot_ws_urls:
  - ws://127.0.0.1:6700 # 端口号要与go-cqhttp一致
  superusers:
  - 123456789 # 超管用户，替换成你的QQ号，将会接收到出错等后台消息
  - 987654321 # 可以指定多个
```

默认情况下，机器人只会响应私聊，如需响应群聊，请修改configs/contexts.yaml
```yaml
groups:
  123456789: [别名] # 替换为群号，别名也可以指定多个或不指定
  987654321: [] # 可指定多个群
private_limit: [1234567890] # 私聊黑名单
private_limit_whitelist: true # 将私聊黑名单反转为白名单
timeout: 600 # 运行/ctx命令后，几秒内不操作，自动运行/ctx exit
# 可指定一部分命令只能在特定群聊内触发，如果要在私聊使用这些命令，有两种情况
# 命令若指定为has_group，机器人会自动检测私聊用户是否在群聊中，适合娱乐命令
# 命令若指定为in_group，需要私聊用户输入/ctx 群号（或者/ctx 别名）手动指定群，适合管理命令
```

所有配置文件，以及配置文件内的选项都是可选的，当配置文件不存在时会在日志中提示，而选项会使用默认值
以后会完善其他配置文件的文档（翻译：🕊️🕊️🕊️）

本项目不使用nb-cli，因此配置完成后直接使用`pdm start`运行机器人即可

## 项目结构
带❎的为gitignore
```
IdhagnBot
├❎📁 configs 配置目录
│└📄 *.yaml 插件配置（如果对应插件没有配置，会在日志中提示）
├📁 plugins Nonebot2插件（含所需的资源）
├❎📁 resources 用户自定义资源
├❎📁 states 状态文件，用于记录缓存、统计数据等（不建议手动编辑）
│└📄 *.yaml 插件状态（状态与配置的区别是，状态可能被自动修改，而配置一定只能手动修改）
├❎📁 user_plugins 用户插件，可以根据自己的需要拓展机器人功能
├📁 util 插件之间共用的代码
├❎📄 .env* Nonebot2配置文件（也可使用configs/bot.yaml，见上文）
├📄 .gitignore
├📄 bot.py 机器人主程序
├📄 pdm.lock
├📄 pyproject.yaml
├📄 README.md
└📄 LICENSE
```

## 特别感谢
* [Nonebot2](https://v2.nonebot.dev/)
* [go-cqhttp](https://docs.go-cqhttp.org/)
* [人生重开模拟器](https://github.com/VickScarlet/lifeRestart)（[我的Python移植版](https://github.com/su226/LifeRestartPy)）
* 部分资源来自[nonebot-plugin-petpet](https://github.com/MeetWq/nonebot-plugin-petpet)、[nonebot-plugin-memes](https://github.com/noneplugin/nonebot-plugin-memes)等
* [stdlib-js/random-base-binomial](https://github.com/stdlib-js/random-base-binomial)（因为我觉得为了一个随机数生成器就引入NumPy有些杀鸡用牛刀就把这个移植到了Python）
* 以及其他参考过的Nonebot2插件和用到的在线API，如[emojimix](https://tikolu.net/emojimix/)
