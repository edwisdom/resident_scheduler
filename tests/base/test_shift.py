import pytest

from base.shift import convert_old_to_new_code


def test_convert_old_to_new_code_examples():
    # Test cases from the docstring examples
    test_cases = [
        ("(LR7m)", "o-L-R-07-M"),  # Optional shift
        ("LR4t", "m-L-R-16-T"),  # Regular shift
        ("LIdw", "m-L-I-14-W"),  # Special case: 2PM-7PM intern shift
        ("LB11w", "m-L-B-14-W"),  # Special case: 2PM-11PM blue shift
    ]

    for old_code, expected in test_cases:
        assert (
            convert_old_to_new_code(old_code) == expected
        ), f"Failed to convert {old_code}. Expected {expected}, got {convert_old_to_new_code(old_code)}"


def test_convert_old_to_new_code_additional_cases():
    # Additional test cases to verify other scenarios
    test_cases = [
        ("LR7m", "m-L-R-07-M"),  # Regular 7AM shift
        ("LR9m", "m-L-R-09-M"),  # Regular 9AM shift
        ("LR11m", "m-L-R-11-M"),  # Regular 11AM shift
        ("LR1m", "m-L-R-13-M"),  # Regular 1PM shift
        ("LR4m", "m-L-R-16-M"),  # Regular 4PM shift
        ("LGnm", "m-L-G-19-M"),  # Night shift
        ("(LRnt)", "o-L-R-19-T"),  # Optional night shift
    ]

    for old_code, expected in test_cases:
        assert (
            convert_old_to_new_code(old_code) == expected
        ), f"Failed to convert {old_code}. Expected {expected}, got {convert_old_to_new_code(old_code)}"


def test_convert_old_to_new_code_invalid_input():
    # Test invalid input handling
    with pytest.raises(ValueError):
        convert_old_to_new_code("LR")  # Too short
