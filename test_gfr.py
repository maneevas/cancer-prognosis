import pytest


def test_calculate_ckd_epi():
    from gui import calculate_ckd_epi

    assert 80 <= calculate_ckd_epi(30, "мужской", 80) <= 120
    assert calculate_ckd_epi(60, "мужской", 120) < 80

    assert calculate_ckd_epi(30, "женский", 80) < calculate_ckd_epi(30, "мужской", 80)

    with pytest.raises(Exception):
        calculate_ckd_epi(-30, "мужской", 80)
    with pytest.raises(Exception):
        calculate_ckd_epi(30, "unknown", 80)