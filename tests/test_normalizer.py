import pytest

from app.modules.preprocessing.normalizer import PersianTextNormalizer

@pytest.fixture
def normalizer():
    return PersianTextNormalizer()

def test_اصلاح_ی_و_ک(normalizer):
    text = "می‌خواهم برنامه‌نویس بشم"
    result = normalizer.normalize(text)
    # "می‌خواهم" با ی فارسی و نیم‌فاصله درست
    assert "می‌خواهم" in result

def test_نیم_فاصله_استاندارد(normalizer):
    text = "می خوام"
    result = normalizer.normalize(text)
    # تبدیل فاصله‌ی نادرست به نیم‌فاصله
    assert "می‌خوام" in result

def test_حذف_نویز(normalizer):
    text = "سلام؛ *** !!! این یک متن است"
    result = normalizer.remove_noise(text)
    assert "***" not in result
    assert "سلام" in result

def test_تفکیک_جملات(normalizer):
    text = "من برنامه‌نویس هستم. الان در حال کارم. فردا برمیگردم"
    sentences = normalizer.split_sentences(text)
    assert len(sentences) == 3
