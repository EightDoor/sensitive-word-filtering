"""真实词库资源测试：源码与 wheel 安装两种形态下资源可读且非空。"""

from importlib import resources

from sensitive_word_filtering import detector


def test_packaged_dictionary_readable_and_large():
    resource = resources.files("sensitive_word_filtering").joinpath(
        "dictionaries/sensitive_word_dict.txt"
    )
    with resource.open("r", encoding="utf-8") as fh:
        words = [line.strip() for line in fh if line.strip()]
    assert len(words) > 60000


def test_detector_hits_real_dictionary_word():
    # 幂等初始化，真实词库（与固定词表单测互不污染：其 fixture 结束后自动恢复）
    detector.initialize()
    assert detector.contains("办理001工程许可") is True
