from util import help, importing

importing.load_children(__name__)

category = help.CategoryItem.find("meme_pic", True)
category.brief = "头像梗图生成器"
category.add(help.StringItem("特别感谢: nonebot-plugin-petpet、lab.magiconch.com"))
category.add(help.StringItem("标有[动]的可以传入动图"))

# 来源参照（是的我改了一部分名字，因为强迫症犯了）
# addict         nonebot-plugin-petpet 上瘾/毒瘾发作
# alike          nonebot-plugin-petpet 一样
# angel          nonebot-plugin-petpet 小天使
# anya           nonebot-plugin-petpet 阿尼亚喜欢
# asciiart       自制（灵感来自 nonebot-plugin-petpet 字符画，代码自行实现）
# ask            nonebot-plugin-petpet 问问/去问问
# away           nonebot-plugin-petpet 不要靠近
# away2          nonebot-plugin-petpet 远离
# bite           nonebot-plugin-petpet 吃
# blood_pressure nonebot-plugin-petpet 高血压
# blue           nonebot-plugin-petpet 群青
# book           nonebot-plugin-petpet 看书
# call_110       nonebot-plugin-petpet 遇到困难请拨打
# captain        nonebot-plugin-petpet 舰长
# china          nonebot-plugin-petpet 国旗
# confuse        nonebot-plugin-petpet 迷惑
# coupon         nonebot-plugin-petpet 兑换券
# cover          nonebot-plugin-petpet 捂脸
# cxk            自制
# decent_kiss    nonebot-plugin-petpet 像样的亲亲
# dianzhongdian  nonebot-plugin-petpet 典中典
# disc           nonebot-plugin-petpet 听音乐
# distracted     nonebot-plugin-petpet 注意力涣散
# eat            nonebot-plugin-petpet 啃
# erode          参考自 LaoLittle/DrawMeme（我寻思着 AGPL 我也不敢复制粘贴啊，下同）
# fencing        nonebot-plugin-petpet 击剑/🤺（有修改）
# fisheye        nonebot-plugin-petpet 哈哈镜
# flash          参考自 LaoLittle/DrawMeme
# flat           nonebot-plugin-petpet 看扁
# follow         nonebot-plugin-petpet 关注
# forever        nonebot-plugin-petpet 永远喜欢/我永远喜欢
# friend         nonebot-plugin-petpet 交个朋友
# getout         nonebot-plugin-petpet 爬
# gun            nonebot-plugin-petpet 手枪
# hammer         nonebot-plugin-petpet 锤
# hit            nonebot-plugin-petpet 敲
# hit_screen     nonebot-plugin-petpet 打穿/打穿屏幕
# hold           nonebot-plugin-petpet 抱紧
# hug_leg        nonebot-plugin-petpet 抱大腿
# icon           nonebot-plugin-petpet 看图标
# impolite       nonebot-plugin-petpet 不文明
# indihome       自制
# interview      nonebot-plugin-petpet 采访
# intimate       nonebot-plugin-petpet 贴/贴贴/蹭/蹭蹭
# jiji_king      nonebot-plugin-petpet 急急国王
# jiujiu         nonebot-plugin-petpet 啾啾
# keep           nonebot-plugin-petpet 一直
# keep_keep      nonebot-plugin-petpet 一直一直
# kidnap         nonebot-plugin-petpet 防诱拐
# kirby          nonebot-plugin-petpet 卡比重锤
# kiss           nonebot-plugin-petpet 亲/亲亲
# knock          nonebot-plugin-petpet 捶
# laptop         nonebot-plugin-petpet 玩游戏/来玩游戏
# loading        nonebot-plugin-petpet 加载中
# louvre         https://lab.magiconch.com/one-last-image/
# love           nonebot-plugin-petpet 永远爱你
# lying          nonebot-plugin-petpet 紧贴/紧紧贴着
# marble         参考自 LaoLittle/DrawMeme
# marry          nonebot-plugin-petpet 结婚申请/结婚登记
# message        nonebot-plugin-petpet 我朋友说/我有个朋友说
# miragetank     自制（算法来自https://zhuanlan.zhihu.com/p/32532733）
# mirror         nonebot-plugin-petpet 对称
# need           nonebot-plugin-petpet 需要/你可能需要
# not_responding nonebot-plugin-petpet 无响应
# ori            自制
# pad            nonebot-plugin-petpet 胡桃平板
# paint          nonebot-plugin-petpet 这像画吗
# painter        nonebot-plugin-petpet 小画家
# pat            nonebot-plugin-petpet 拍
# patina         https://magiconch.com/patina/
# perfect        nonebot-plugin-petpet 完美/完美的
# petpet         nonebot-plugin-petpet 摸/摸摸/摸头/摸摸头/rua
# play           nonebot-plugin-petpet 顶/玩
# police         nonebot-plugin-petpet 警察（有修改）
# police2        nonebot-plugin-petpet 出警
# pound          nonebot-plugin-petpet 捣
# protogen       自制
# prpr           nonebot-plugin-petpet 舔/舔屏/prpr
# punch          nonebot-plugin-petpet 打拳
# rip            nonebot-plugin-petpet 撕
# rip2           nonebot-plugin-petpet 怒撕
# roll           nonebot-plugin-petpet 滚
# rub            nonebot-plugin-petpet 搓
# safe_sense     nonebot-plugin-petpet 安全感
# shock          nonebot-plugin-petpet 震惊
# sign           nonebot-plugin-petpet 唐可可举牌
# slap           自制
# spin           nonebot-plugin-petpet 转
# suck           nonebot-plugin-petpet 吸/嗦
# support        nonebot-plugin-petpet 精神支柱
# teach          nonebot-plugin-petpet 讲课/敲黑板
# think          nonebot-plugin-petpet 想什么
# throw          nonebot-plugin-petpet 丢/扔
# throw2         nonebot-plugin-petpet 抛/掷
# together       nonebot-plugin-petpet 一起
# tomb           自制
# trash          nonebot-plugin-petpet 垃圾/垃圾桶
# tv             自制
# virgin         自制
# wallpaper      nonebot-plugin-petpet 墙纸
# wantwant       自制
# watermelon     自制
# wave           nonebot-plugin-petpet 波纹
# why_at_me      nonebot-plugin-petpet 为什么@我/为什么at我
# wife           nonebot-plugin-petpet 我老婆
# windows        自制
# work           nonebot-plugin-petpet 继续干活/打工人
# worship        nonebot-plugin-petpet 膜/膜拜
# zoom           nonebot-plugin-petpet 胡桃放大
