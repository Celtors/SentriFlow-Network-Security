import pytest

from sentriflow.inspection.luhn import valid_luhn


@pytest.mark.parametrize(
    "value,valid",
    [
        ("4111 1111 1111 1111", True),
        ("5555-5555-5555-4444", True),
        ("4111111111111112", False),
        ("0000000000000000", False),
        ("12", False),
    ],
)
def test_card_checksum(value, valid):
    assert valid_luhn(value) is valid
