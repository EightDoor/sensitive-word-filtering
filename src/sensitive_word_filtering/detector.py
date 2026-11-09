"""敏感词检测引擎：启动期构建只读 Aho-Corasick 自动机，请求期只读复用。

词库为 houbb/sensitive-word-data 的中文主词库（来源与更新方式见 ``dictionaries/NOTICE.md``）。
词库与输入统一归一化：NFKC + 忽略英文大小写；不忽略空格与标点——
刻意行为：跳字符匹配会把不连续的正常文本误判为命中。
"""
from __future__ import annotations

import threading
import unicodedata
from importlib import resources

import ahocorasick

_DICT_PACKAGE = "sensitive_word_filtering"
_DICT_FILE = "dictionaries/sensitive_word_dict.txt"

_lock = threading.Lock()
_automaton: ahocorasick.Automaton | None = None


def normalize_text(text: str) -> str:
    """词库与输入共用的归一化：NFKC 折叠兼容字符 + 英文小写。"""
    return unicodedata.normalize("NFKC", text).casefold()


def _load_words() -> list[str]:
    """读包内词库并归一化；文件缺失 / 不可读 / 编码错误直接抛错（启动 fail-closed）。"""
    resource = resources.files(_DICT_PACKAGE).joinpath(_DICT_FILE)
    words: list[str] = []
    seen: set[str] = set()
    try:
        with resource.open("r", encoding="utf-8") as fh:
            for line in fh:
                word = normalize_text(line.strip())
                if not word or word in seen:
                    continue
                seen.add(word)
                words.append(word)
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"敏感词词库读取失败: {_DICT_FILE}") from exc
    return words


def initialize() -> None:
    """构建自动机；幂等，构建成功后整体替换全局引用，请求期只读共享。

    词库有效词条为零时抛 RuntimeError——宁可启动失败，不允许无过滤状态运行。
    """
    global _automaton
    if _automaton is not None:
        return
    with _lock:
        if _automaton is not None:
            return
        words = _load_words()
        if not words:
            raise RuntimeError("敏感词词库为空，拒绝启动（fail-closed）")
        automaton = ahocorasick.Automaton()
        for word in words:
            automaton.add_word(word, True)
        automaton.make_automaton()
        _automaton = automaton


def is_ready() -> bool:
    """自动机是否已就绪（health 端点用）。"""
    return _automaton is not None


def contains(text: str) -> bool:
    """判断文本是否包含敏感词，命中即停。未初始化时抛错，不静默放行。"""
    automaton = _automaton
    if automaton is None:
        raise RuntimeError("敏感词检测器未初始化")
    if not text:
        return False
    return next(automaton.iter(normalize_text(text)), None) is not None
