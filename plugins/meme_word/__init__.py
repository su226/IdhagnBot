from util import help, importing

importing.load_children(__name__)

category = help.CategoryItem.find("meme_word", True)
category.brief = "文字梗图生成器"
