import pytest

from sentriflow.inspection.luhn import is_valid_card


@pytest.mark.parametrize(
    "value", ["4111111111111111", "4111-1111-1111-1111", "5555 5555 5555 4444"]
)
def test_dummy_cards(value):
    assert is_valid_card(value)


@pytest.mark.parametrize(
    "value", ["4111111111111112", "0000000000000000", "１２３４", "123", "x" * 16]
)
def test_invalid_cards(value):
    assert not is_valid_card(value)
