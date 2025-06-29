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
    def from_str(cls, day_str: str) -> "DayOfWeek":
        """Convert a full day name (like 'Monday') to the enum member"""
        day_name = day_str.upper()
        for day in cls:
            if day.name == day_name:
                return day
        raise ValueError(f"No DayOfWeek found for '{day_str}'")

    def to_full_str(self) -> str:
        return self.name.upper()

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


@dataclass
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


@dataclass
class Resident:
    """Represents a medical resident with their details and constraints"""

    name: str
    pgy_level: PGYLevel
    service_type: ServiceType
    hours_goal: int
    requests_off: list[date] = field(default_factory=list)
    current_hours: int = 0
