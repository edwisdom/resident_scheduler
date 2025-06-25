from dataclasses import dataclass
from datetime import datetime
from typing import Callable, TypeAlias

from src.base.objects import DayOfWeek, Hospital, PGYLevel, Team


def convert_old_to_new_code(old_code: str) -> str:
    """
    Converts old shift code format to the new format:
    "{Optional}-{Hospital}-{Team}-{Start_Time_in_24hr_format}-{Day}"

    Examples:
    - (LR7m) -> o-L-R-07-M
    - LR4t -> m-L-R-16-T
    - LIdw -> m-L-I-14-W (special case)
    - LB11w -> m-L-B-14-W (special case)
    """
    # Handle optional shifts
    is_optional = old_code.startswith("(") and old_code.endswith(")")
    optional_prefix = "o" if is_optional else "m"
    if is_optional:
        old_code = old_code[1:-1]

    # Handle special cases first
    special_cases = {
        "LIdw": f"{optional_prefix}-L-I-14-W",  # 2PM-7PM intern shift on Wednesday
        "LB11w": f"{optional_prefix}-L-B-14-W",  # 2PM-11PM blue shift on Wednesday
    }
    if old_code in special_cases:
        return special_cases[old_code]

    # Extract hospital, team, time, and day
    if len(old_code) < 4:
        raise ValueError("Invalid shift code format")

    hospital = old_code[0]
    team = old_code[1]
    time_spec = old_code[2:-1]
    day = old_code[-1].upper()

    # Parse start time
    start_time = ""

    if time_spec == "d":
        start_time = "07"  # 7AM day shift
    elif time_spec == "n":
        start_time = "19"  # 7PM night shift
    else:
        hour = int(time_spec)
        # Only 7, 9, 11 are AM shifts per requirements
        if hour in [7, 9, 11]:
            start_time = f"{hour:02d}"
        else:
            # Everything else is PM
            start_time = f"{(hour % 12) + 12:02d}"

    # Combine all parts with dashes
    return f"{optional_prefix}-{hospital}-{team}-{start_time}-{day}"


Hour: TypeAlias = int


@dataclass
class Shift:
    """Represents a work shift with its properties"""

    hospital: Hospital
    team: Team
    start_time: datetime
    day: DayOfWeek
    code: str
    is_mandatory: bool = True

    @property
    def duration(self) -> Callable[[PGYLevel], Hour]:
        """
        Returns a function that calculates the duration of the shift in hours based on the PGY level.

        Rules:
        - PGY-1 shifts are all 12 hours long
        - PGY-2 and PGY-3 shifts are all 10 hours long
        - If a PGY-1 is scheduled for Eval, their shift lasts 10 hours (same as PGY-2/3)
        - Peds shifts are always 10 hours long regardless of PGY year
        - Special cases: LIdw (2PM-7PM) is 5 hours, LB11w (2PM-11PM) is 9 hours
        """

        def get_duration(level: PGYLevel) -> Hour:
            # Special cases first
            if self.code == "m-L-I-14-W":  # LIdw
                return 5  # 2PM-7PM intern shift on Wednesday
            elif self.code == "m-L-B-14-W":  # LB11w
                return 9  # 2PM-11PM blue shift on Wednesday

            # Peds shifts are always 10 hours
            if self.team == Team.PEDS:
                return 10

            # Eval shifts are 10 hours for all PGY levels
            if self.team == Team.EVAL:
                return 10

            # Default durations based on PGY levelå
            if level == PGYLevel.PGY1:
                return 12  # PGY-1 shifts are 12 hours
            else:
                return 10  # PGY-2 and PGY-3 shifts are 10 hours

        return get_duration

    @classmethod
    def from_code(cls, code: str) -> "Shift":
        components = code.split("-")
        num_expected = 5

        if len(components) != num_expected:
            raise ValueError(
                f"Broke code into {components}, expected it to have {num_expected} components"
            )

        mandatory, hospital, team, start_time_str, day_of_week = components

        # Parse start time as datetime (using a default date)
        hour = int(start_time_str)
        start_time = datetime(2024, 1, 1, hour, 0)  # Default date, only time matters

        return cls(
            is_mandatory=(mandatory == "m"),
            hospital=Hospital(name=hospital),
            team=Team(team),
            start_time=start_time,
            day=DayOfWeek(day_of_week),
            code=code,
        )
