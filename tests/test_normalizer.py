from app.modules.preprocessing.normalizer import PersianTextNormalizer


def test_persian_characters_and_half_space():
    result = PersianTextNormalizer().normalize("ي و ك؛ می خواهم برنامه نویس باشم")
    assert "ی" in result
    assert "ک" in result
    assert "می‌خواهم" in result


def test_contacts_are_preserved():
    result = PersianTextNormalizer().remove_noise("ایمیل ali@example.com و سایت https://example.com")
    assert "ali@example.com" in result
    assert "https://example.com" in result


def test_sentence_split():
    result = PersianTextNormalizer().split_sentences(
        "من برنامه‌نویس هستم. در تهران کار می‌کنم. به پروژه‌های متن‌باز علاقه دارم."
    )
    assert len(result) == 3
