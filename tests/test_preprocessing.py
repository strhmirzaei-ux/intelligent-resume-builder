import pytest

from app.modules.preprocessing.normalizer import PersianTextNormalizer


def test_normalizer_rejects_non_string():
    with pytest.raises(TypeError):
        PersianTextNormalizer().normalize(None)  # type: ignore[arg-type]
