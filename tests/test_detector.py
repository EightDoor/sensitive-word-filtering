"""检测核心单测：固定词表覆盖归一化、fail-closed 与命中即停。"""

import pytest

from sensitive_word_filtering import detector

FIXTURE_WORDS = ["001工程", "aot9527", "测试违禁词"]


@pytest.fixture
def ready(monkeypatch):
    """用固定词表构建自动机；monkeypatch 结束后自动恢复原全局状态。"""
    monkeypatch.setattr(detector, "_automaton", None)
    monkeypatch.setattr(detector, "_load_words", lambda: list(FIXTURE_WORDS))
    detector.initialize()
    return detector


def test_hit(ready):
    assert ready.contains("随便一段aot9527的文本") is True


def test_miss(ready):
    assert ready.contains("请问明天天气怎么样") is False


def test_case_insensitive(ready):
    # 词库词条为小写，输入大写经 casefold 后仍命中
    assert ready.contains("AOT9527") is True


def test_full_width_normalized(ready):
    assert ready.contains("００１工程") is True


def test_space_breaks_match(ready):
    # 首版明确不忽略空格与标点
    assert ready.contains("001 工程") is False
    assert ready.contains("001·工程") is False


def test_empty_text_not_hit(ready):
    assert ready.contains("") is False


def test_normalize_text():
    assert detector.normalize_text("ＡＢＣ１２３") == "abc123"


def test_uninitialized_raises(monkeypatch):
    """未初始化时检测抛错而非静默返回未命中。"""
    monkeypatch.setattr(detector, "_automaton", None)
    with pytest.raises(RuntimeError, match="未初始化"):
        detector.contains("你好")


def test_missing_dictionary_fails_initialize(monkeypatch):
    monkeypatch.setattr(detector, "_automaton", None)
    monkeypatch.setattr(detector, "_DICT_FILE", "dictionaries/__missing_dict__.txt")
    with pytest.raises(RuntimeError, match="词库读取失败"):
        detector.initialize()


def test_empty_dictionary_fails_initialize(monkeypatch):
    monkeypatch.setattr(detector, "_automaton", None)
    monkeypatch.setattr(detector, "_load_words", lambda: [])
    with pytest.raises(RuntimeError, match="词库为空"):
        detector.initialize()


def test_initialize_is_idempotent(ready):
    before = detector._automaton
    assert before is not None
    detector.initialize()
    assert detector._automaton is before


def test_is_ready_reflects_state(monkeypatch):
    monkeypatch.setattr(detector, "_automaton", None)
    assert detector.is_ready() is False
    monkeypatch.setattr(detector, "_load_words", lambda: list(FIXTURE_WORDS))
    detector.initialize()
    assert detector.is_ready() is True


def test_contains_stops_at_first_match(monkeypatch):
    """命中即停：next() 只消费自动机第一个结果，不扫描剩余文本。"""

    class _CountingAutomaton:
        def __init__(self):
            self.consumed = 0

        def iter(self, _text):
            def gen():
                self.consumed += 1
                yield True
                self.consumed += 1
                yield True

            return gen()

    stub = _CountingAutomaton()
    monkeypatch.setattr(detector, "_automaton", stub)
    assert detector.contains("任意文本") is True
    assert stub.consumed == 1
