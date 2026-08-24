import pytest

from app.modules.preprocessing.normalizer import PersianTextNormalizer


@pytest.fixture
def normalizer():
    return PersianTextNormalizer()


def test_normalizes_persian_characters(normalizer):
    assert normalizer.normalize("ي و ك") == "ی و ک"


def test_normalizes_informal_prefix_spacing(normalizer):
    assert "می‌خوام" in normalizer.normalize("می خوام")


def test_removes_noise_without_destroying_contacts(normalizer):
    result = normalizer.remove_noise(
        "سلام؛ *** ایمیل ali@example.com و سایت https://example.com"
    )
    assert "***" not in result
    assert "ali@example.com" in result
    assert "https://example.com" in result


def test_splits_sentences(normalizer):
    sentences = normalizer.split_sentences(
        "من برنامه‌نویس هستم. الان در حال کارم. فردا برمی‌گردم."
    )
    assert len(sentences) == 3
