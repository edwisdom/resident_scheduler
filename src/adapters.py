from datetime import datetime
from pathlib import Path

import pandas as pd

from src.base.objects import DayOfWeek, PGYLevel, Resident, ServiceType
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


def read_residents(filename: Path) -> list[Resident]:
    df = pd.read_csv(filename)

    residents = []

    for _, row in df.iterrows():
        # Extract basic info
        name = str(row["Resident"]).strip()
        pgy_int = int(row["PGY"])
        service_str = str(row["Service"]).strip()
        hours_goal = int(row["Hours/Block Goal"])

        # Convert PGY to enum
        pgy_level = PGYLevel(pgy_int)

        # Convert service to enum
        service_type = ServiceType(service_str)

        # Parse requests (dates)
        requests_off = []
        requests_raw = row.get("Requests", "")

        if pd.notna(requests_raw) and str(requests_raw).strip():
            # Split by comma and parse each date
            date_strings = [d.strip() for d in str(requests_raw).split(",")]
            for date_str in date_strings:
                if date_str:  # Skip empty strings
                    try:
                        parsed_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                        requests_off.append(parsed_date)
                    except ValueError as e:
                        print(
                            f"Warning: Could not parse date '{date_str}' for resident {name}: {e}"
                        )

        # Create resident object
        resident = Resident(
            name=name,
            pgy_level=pgy_level,
            service_type=service_type,
            hours_goal=hours_goal,
            requests_off=tuple(requests_off),
        )

        residents.append(resident)

    return residents
