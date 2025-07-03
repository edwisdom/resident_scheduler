from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class DayOfWeek(Enum):
    MONDAY = "M"
    TUESDAY = "T"
    WEDNESDAY = "W"
    THURSDAY = "R"
    FRIDAY = "F"
    SATURDAY = "S"
    SUNDAY = "U"

    @classmethod
    def from_date(cls, date_obj: date) -> "DayOfWeek":
        """Convert a date object to the corresponding DayOfWeek enum"""
        day_mapping = {
            0: cls.MONDAY,  # Monday
            1: cls.TUESDAY,  # Tuesday
            2: cls.WEDNESDAY,  # Wednesday
            3: cls.THURSDAY,  # Thursday
            4: cls.FRIDAY,  # Friday
            5: cls.SATURDAY,  # Saturday
            6: cls.SUNDAY,  # Sunday
        }
        return day_mapping[date_obj.weekday()]

    def to_full_str(self) -> str:
        return self.name.upper()

    @classmethod
    def from_str(cls, day_name: str) -> "DayOfWeek":
        """Convert a string day name to the corresponding DayOfWeek enum"""
        day_name_upper = day_name.upper()
        for day in cls:
            if day.name.upper() == day_name_upper:
                return day
        raise ValueError(f"Invalid day name: {day_name}")

    @classmethod
    def values(cls) -> set[str]:
        """Return all enum values as a set of strings"""
        return {day.value for day in cls}


class PGYLevel(Enum):
    PGY1 = 1
    PGY2 = 2
    PGY3 = 3


class ServiceType(Enum):
    ED = "ED"
    OFF_SERVICE = "Off-Service"
    VACATION = "Vacation"
    PEDS = "Peds"


@dataclass(frozen=True)
class Hospital:
    name: str


@dataclass
class HospitalSystem:
    name: str
    hospitals: list[Hospital] = field(default_factory=list)


class Team(Enum):
    RED = "R"  # PGY-3 only
    GREEN = "G"  # PGY-2 only
    INTERN = "I"  # PGY-1 only
    EVAL = "E"  # Any resident, prefer PGY-1
    BLUE = "B"  # PGY-1 required, can add PGY-2/3
    PEDS = "P"  # Prefer PGY-1, can use PGY-2/3 if needed


@dataclass(frozen=True)
class Resident:
    """Represents a medical resident with their details and constraints"""

    name: str
    pgy_level: PGYLevel
    service_type: ServiceType
    hours_goal: int
    requests_off: tuple[date, ...] = field(default_factory=tuple)
    current_hours: int = 0
