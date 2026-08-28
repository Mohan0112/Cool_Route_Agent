import pytest

from app.agents.coolroute_agent import heat_risk_category


def test_heat_risk_category_none_is_unknown():
    category, _tip = heat_risk_category(None)
    assert category == "Unknown"


@pytest.mark.parametrize(
    "temp_c,expected_category",
    [
        (10.0, "Comfortable"),
        (26.9, "Comfortable"),
        (27.0, "Caution"),
        (31.9, "Caution"),
        (32.0, "Extreme Caution"),
        (38.9, "Extreme Caution"),
        (39.0, "Danger"),
        (50.9, "Danger"),
        (51.0, "Extreme Danger"),
        (60.0, "Extreme Danger"),
    ],
)
def test_heat_risk_category_boundaries(temp_c, expected_category):
    category, _tip = heat_risk_category(temp_c)
    assert category == expected_category


def test_heat_risk_category_always_returns_a_nonempty_tip():
    for temp_c in [None, 10, 30, 40, 55]:
        _category, tip = heat_risk_category(temp_c)
        assert tip
