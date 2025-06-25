from pathlib import Path

import pandas as pd

from src.base.objects import DayOfWeek
from src.base.shift import Shift, convert_old_to_new_code


def read_shifts(filename: Path) -> list[Shift]:
    df = pd.read_csv(filename)

    shifts = []
    expected_columns = {day.to_full_str() for day in DayOfWeek}

    if set(df.columns) != expected_columns:
        raise ValueError(
            f"Columns do not match DayOfWeek expectations {expected_columns}, got {df.columns}"
        )

    # Process each column that represents a day
    for column in df.columns:
        day_letter = DayOfWeek.from_str(column).value.lower()

        for _, row in df.iterrows():
            raw_shift_code = row[column]

            # Skip empty cells (NaN values)
            if pd.isna(raw_shift_code) or raw_shift_code == "":
                continue

            shift_code = str(raw_shift_code).strip()

            is_optional = shift_code.startswith("(") and shift_code.endswith(")")
            inner_code = shift_code[1:-1] if is_optional else shift_code
            has_day_info = inner_code[-1].upper() in DayOfWeek.values()
            old_inner_code = inner_code if has_day_info else inner_code + day_letter
            old_code = old_inner_code if not is_optional else f"({old_inner_code})"

            try:
                new_code = convert_old_to_new_code(old_code)
                shift = Shift.from_code(new_code)
                shifts.append(shift)

            except (ValueError, KeyError) as e:
                # Skip invalid shift codes but log them for debugging
                print(f"Warning: Could not parse shift code '{old_code}': {e}")
                continue

    return shifts
