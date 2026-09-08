import html
import logging
from html.parser import HTMLParser


_TITLE_MARKUP_TAGS = frozenset({"bold", "italic", "sup", "sub"})
_LOGGER = logging.getLogger(__name__)


class _BalancedInlineMarkupParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.stack = []
        self.valid = True

    def handle_starttag(self, tag, attrs):
        if tag not in _TITLE_MARKUP_TAGS:
            self.valid = False
            return
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag not in _TITLE_MARKUP_TAGS or not self.stack or self.stack[-1] != tag:
            self.valid = False
            return
        self.stack.pop()

    def handle_startendtag(self, tag, attrs):
        self.valid = False

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append(html.unescape(f"&{name};"))

    def handle_charref(self, name):
        self.parts.append(html.unescape(f"&#{name};"))

    def handle_comment(self, data):
        self.valid = False

    def handle_decl(self, decl):
        self.valid = False

    def unknown_decl(self, data):
        self.valid = False


def clean_title_text(value):
    """清除标题中严格配对的已知格式标签，异常结构保留原文。"""
    original = str(value or "")
    parser = _BalancedInlineMarkupParser()
    try:
        parser.feed(original)
        parser.close()
    except (ValueError, AssertionError):
        return original.strip()
    if not parser.valid or parser.stack:
        if any(f"<{tag}" in original.lower() or f"</{tag}" in original.lower() for tag in _TITLE_MARKUP_TAGS):
            _LOGGER.warning("标题包含未配对或不支持的内联标记，已保留原文: %s", original)
        return original.strip()
    return "".join(parser.parts).strip()


def normalize_title_text(value):
    """生成跨来源标题匹配键：清洗格式、压缩空白并忽略大小写。"""
    return " ".join(clean_title_text(value).split()).casefold()
