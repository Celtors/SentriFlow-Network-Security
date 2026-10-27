def is_valid_card(value: str) -> bool:
    digits = value.replace(" ", "").replace("-", "")
    if not digits.isascii() or not digits.isdigit() or not 13 <= len(digits) <= 19:
        return False
    if len(set(digits)) == 1:
        return False
    numbers = [int(d) for d in digits]
    for i in range(len(numbers) - 2, -1, -2):
        numbers[i] = numbers[i] * 2 - (9 if numbers[i] >= 5 else 0)
    return sum(numbers) % 10 == 0
