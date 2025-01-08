from util import help, importing

importing.load_children(__name__)

category = help.CategoryItem.find("memes", True)
category.data.node_str = "memes"
category.brief = "梗图生成器"

# 来源参照
# addict         自制
# cxk            自制
# erode          参考自 LaoLittle/DrawMeme（我寻思着 AGPL 我也不敢复制粘贴啊，下同）
# flash          参考自 LaoLittle/DrawMeme
# indihome       自制
# lolcat         自制
# louvre         https://lab.magiconch.com/one-last-image/
# marble         参考自 LaoLittle/DrawMeme
# meme_generator 使用 MemeCrafters/meme-generator
# miragetank     自制（算法来自https://zhuanlan.zhihu.com/p/32532733）
# nokia          自制
# ori            自制
# orly           https://orly.nanmu.me/
# patina         https://magiconch.com/patina/
# protogen       自制
# slap           自制
# tv             自制
# virgin         自制
# wantwant       自制
# watermelon     自制
# windows        自制
