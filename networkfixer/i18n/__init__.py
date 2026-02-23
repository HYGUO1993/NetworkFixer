# -*- coding: utf-8 -*-
"""国际化模块 - 提供 NetworkFixer 的多语言支持

使用方法:
    from networkfixer.i18n import t, detect_system_language
    text = t('app.title', 'zh_CN')  # 返回 "网络修复工具"
"""

from .base import t, get_available_languages, detect_system_language, register_translations

# 导入翻译模块，自动注册翻译字典
from . import zh_CN  # 注册中文翻译
from . import en_US  # 注册英文翻译

__all__ = [
    "t",
    "get_available_languages",
    "detect_system_language",
    "register_translations",
]
