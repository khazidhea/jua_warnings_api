from typing import Optional


def find_closest_number(value: float, values: list[float]) -> Optional[float]:
    """get closest to value number from values"""

    closest_value = None
    closest_distance = float("inf")
    for num in values:
        distance = abs(num - value)
        if distance < closest_distance:
            closest_distance = distance
            closest_value = num
    return closest_value
