import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from base.objects import Hospital, HospitalSystem, PGYLevel, Resident, ServiceType, Team
from base.shift import Shift, ShiftTemplate, generate_shifts_for_date_range


class ConstraintType(Enum):
    HARD = "hard"
    SOFT = "soft"


@dataclass
class ConstraintSpec:
    """Specification for a constraint to be added to the model"""

    name: str
    constraint_func: Callable[[], List[cp_model.Constraint]]
    constraint_type: ConstraintType = ConstraintType.HARD
    enabled: bool = True


@dataclass
class ScheduleModel:
    """Represents the scheduling problem model for the CP-SAT solver"""

    residents: List[Resident]
    shifts: List[Shift]  # Now these are actual shift instances, not templates
    days: List[date]
    hospital_system: HospitalSystem

    # Maps for efficient lookups
    residents_by_pgy: Dict[PGYLevel, List[Resident]] = field(init=False)
    shifts_by_day: Dict[date, List[Shift]] = field(init=False)
    shifts_by_team: Dict[Team, List[Shift]] = field(init=False)
    shifts_by_hospital: Dict[Hospital, List[Shift]] = field(init=False)

    # CP-SAT model components
    model: cp_model.CpModel = field(init=False)
    solver: cp_model.CpSolver = field(init=False)
    assignments: Dict[Tuple[date, Shift, Resident], cp_model.IntVar] = field(init=False)
    objective_terms: List[cp_model.LinearExpr] = field(init=False)

    def __post_init__(self):
        """Initialize the model components"""
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.objective_terms = []

        # Create lookup maps
        self._create_lookup_maps()

        # Create assignment variables
        self._create_assignment_variables()

    def _create_lookup_maps(self):
        """Create efficient lookup maps for residents and shifts"""
        # Group residents by PGY level
        self.residents_by_pgy = {}
        for pgy in PGYLevel:
            self.residents_by_pgy[pgy] = [
                r for r in self.residents if r.pgy_level == pgy
            ]

        # Group shifts by day - now much simpler since shifts have actual dates
        self.shifts_by_day = {}
        for day in self.days:
            self.shifts_by_day[day] = [s for s in self.shifts if s.date == day]

        # Group shifts by team
        self.shifts_by_team = {}
        for team in Team:
            self.shifts_by_team[team] = [s for s in self.shifts if s.team == team]

        # Group shifts by hospital
        self.shifts_by_hospital = {}
        for hospital in self.hospital_system.hospitals:
            self.shifts_by_hospital[hospital] = [
                s for s in self.shifts if s.hospital.name == hospital.name
            ]

    def _create_assignment_variables(self):
        """Create binary variables for each possible assignment"""
        self.assignments = {}

        # Only create variables for eligible residents
        eligible_residents = [
            r
            for r in self.residents
            if r.service_type not in [ServiceType.OFF_SERVICE, ServiceType.VACATION]
        ]

        for day in self.days:
            for shift in self.shifts_by_day[day]:
                for resident in eligible_residents:
                    key = (day, shift, resident)
                    self.assignments[key] = self.model.NewBoolVar(
                        f"assign_{day.strftime('%Y-%m-%d')}_{shift.code}_{resident.name}"
                    )

    def get_constraint_specs(self) -> List[ConstraintSpec]:
        """Get all available constraint specifications"""
        return [
            ConstraintSpec("shift_assignment", self._shift_assignment_constraints),
            # ConstraintSpec("resident_daily", self._resident_daily_constraints),
            # ConstraintSpec("continuous_hours", self._continuous_hours_constraints),
            # ConstraintSpec("weekly_hours", self._weekly_hours_constraints),
            # ConstraintSpec("team_assignment", self._team_constraints),
            # ConstraintSpec("rest_periods", self._rest_period_constraints),
            # ConstraintSpec("day_off", self._day_off_constraints),
            # ConstraintSpec(
            #     "hour_goals", self._hour_goal_constraints, ConstraintType.SOFT
            # ),
            # ConstraintSpec(
            #     "alternating_hospitals",
            #     self._alternating_hospital_constraints,
            #     ConstraintType.SOFT,
            # ),
            # ConstraintSpec("time_off", self._time_off_constraints, ConstraintType.SOFT),
            # ConstraintSpec(
            #     "circadian_rhythm",
            #     self._circadian_rhythm_constraints,
            #     ConstraintType.SOFT,
            # ),
        ]

    def _shift_assignment_constraints(self) -> List[cp_model.Constraint]:
        """Each mandatory shift must be assigned to exactly one resident"""
        constraints = []
        for day in self.days:
            for shift in self.shifts_by_day[day]:
                if shift.is_mandatory:
                    constraints.append(
                        self.model.Add(
                            sum(
                                self.assignments[(day, shift, resident)]
                                for resident in self.residents
                                if (day, shift, resident) in self.assignments
                            )
                            == 1
                        )
                    )
        return constraints

    def _resident_daily_constraints(self) -> List[cp_model.Constraint]:
        """Each resident can only work one shift per day"""
        constraints = []
        for day in self.days:
            for resident in self.residents:
                if resident.service_type in [ServiceType.ED, ServiceType.PEDS]:
                    constraints.append(
                        self.model.Add(
                            sum(
                                self.assignments[(day, shift, resident)]
                                for shift in self.shifts_by_day[day]
                                if (day, shift, resident) in self.assignments
                            )
                            <= 1
                        )
                    )
        return constraints

    def _continuous_hours_constraints(self) -> List[cp_model.Constraint]:
        """No resident can work more than 12 continuous hours"""
        constraints = []
        for day in self.days:
            # Group shifts by start time
            shifts_by_start_time = {}
            for shift in self.shifts_by_day[day]:
                start_hour = shift.start_time.hour  # Now using time object
                if start_hour not in shifts_by_start_time:
                    shifts_by_start_time[start_hour] = []
                shifts_by_start_time[start_hour].append(shift)

            # For each resident
            for resident in self.residents:
                if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                    continue

                # For each possible shift start time
                for start_hour, shifts in shifts_by_start_time.items():
                    # Find overlapping shifts within 12 hours
                    overlapping_shifts = []
                    for other_start_hour, other_shifts in shifts_by_start_time.items():
                        if (other_start_hour - start_hour) % 24 < 12:
                            overlapping_shifts.extend(other_shifts)

                    # Ensure resident doesn't work more than one overlapping shift
                    if len(overlapping_shifts) > 1:
                        constraints.append(
                            self.model.Add(
                                sum(
                                    self.assignments[(day, shift, resident)]
                                    for shift in overlapping_shifts
                                    if (day, shift, resident) in self.assignments
                                )
                                <= 1
                            )
                        )
        return constraints

    def _weekly_hours_constraints(self) -> List[cp_model.Constraint]:
        """No resident can work more than 60 hours per week"""
        constraints = []

        # Group days by week
        weeks = {}
        for day in self.days:
            week_start = day - timedelta(days=day.weekday())
            if week_start not in weeks:
                weeks[week_start] = []
            weeks[week_start].append(day)

        # For each week and each resident
        for week_start, week_days in weeks.items():
            for resident in self.residents:
                if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                    continue

                # Calculate total hours for this resident in this week
                total_hours = 0
                for day in week_days:
                    for shift in self.shifts_by_day[day]:
                        if (day, shift, resident) in self.assignments:
                            duration = shift.duration(resident.pgy_level)
                            total_hours += (
                                self.assignments[(day, shift, resident)] * duration
                            )

                # Ensure total hours doesn't exceed 60
                if total_hours > 0:
                    constraints.append(self.model.Add(total_hours <= 60))

        return constraints

    def _team_constraints(self) -> List[cp_model.Constraint]:
        """Enforce team-specific constraints"""
        constraints = []

        # Red team (R) must be staffed by PGY-3s
        for day in self.days:
            for shift in self.shifts_by_team.get(Team.RED, []):
                if day in self.shifts_by_day:
                    constraints.append(
                        self.model.Add(
                            sum(
                                self.assignments[(day, shift, resident)]
                                for resident in self.residents_by_pgy[PGYLevel.PGY3]
                                if (day, shift, resident) in self.assignments
                            )
                            == 1
                        )
                    )

        # Similar constraints for other teams
        for day in self.days:
            # Green team (G) must be staffed by PGY-2s
            for shift in self.shifts_by_team.get(Team.GREEN, []):
                if day in self.shifts_by_day:
                    constraints.append(
                        self.model.Add(
                            sum(
                                self.assignments[(day, shift, resident)]
                                for resident in self.residents_by_pgy[PGYLevel.PGY2]
                                if (day, shift, resident) in self.assignments
                            )
                            == 1
                        )
                    )

            # Intern team (I) must be staffed by PGY-1s
            for shift in self.shifts_by_team.get(Team.INTERN, []):
                if day in self.shifts_by_day:
                    constraints.append(
                        self.model.Add(
                            sum(
                                self.assignments[(day, shift, resident)]
                                for resident in self.residents_by_pgy[PGYLevel.PGY1]
                                if (day, shift, resident) in self.assignments
                            )
                            == 1
                        )
                    )

            # Blue team (B) must have at least one PGY-1
            for shift in self.shifts_by_team.get(Team.BLUE, []):
                if day in self.shifts_by_day:
                    constraints.append(
                        self.model.Add(
                            sum(
                                self.assignments[(day, shift, resident)]
                                for resident in self.residents_by_pgy[PGYLevel.PGY1]
                                if (day, shift, resident) in self.assignments
                            )
                            >= 1
                        )
                    )

        return constraints

    def _rest_period_constraints(self) -> List[cp_model.Constraint]:
        """Ensure residents have equivalent rest periods between shifts"""
        constraints = []

        for day_idx, day in enumerate(self.days):
            if day_idx == 0:
                continue

            prev_day = self.days[day_idx - 1]

            for resident in self.residents:
                if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                    continue

                # For each shift on the current day
                for shift in self.shifts_by_day[day]:
                    if (day, shift, resident) not in self.assignments:
                        continue

                    duration = shift.duration(resident.pgy_level)

                    # For each shift on the previous day
                    for prev_shift in self.shifts_by_day[prev_day]:
                        if (prev_day, prev_shift, resident) not in self.assignments:
                            continue

                        prev_duration = prev_shift.duration(resident.pgy_level)
                        rest_period = 24 - prev_duration

                        # If rest period is insufficient, add constraint
                        if rest_period < duration:
                            constraints.append(
                                self.model.Add(
                                    self.assignments[(prev_day, prev_shift, resident)]
                                    + self.assignments[(day, shift, resident)]
                                    <= 1
                                )
                            )

        return constraints

    def _day_off_constraints(self) -> List[cp_model.Constraint]:
        """Ensure residents have at least one day off per week"""
        constraints = []

        # Group days by week
        weeks = {}
        for day in self.days:
            week_start = day - timedelta(days=day.weekday())
            if week_start not in weeks:
                weeks[week_start] = []
            weeks[week_start].append(day)

        # For each week and each resident
        for week_start, week_days in weeks.items():
            for resident in self.residents:
                if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                    continue

                # Sum of assignments for this resident in this week
                week_assignments = sum(
                    self.assignments[(day, shift, resident)]
                    for day in week_days
                    for shift in self.shifts_by_day[day]
                    if (day, shift, resident) in self.assignments
                )

                # Ensure at least one day off
                days_in_week = len(week_days)
                if week_assignments > 0:
                    constraints.append(
                        self.model.Add(week_assignments <= days_in_week - 1)
                    )

        return constraints

    def _hour_goal_constraints(self) -> List[cp_model.Constraint]:
        """Try to meet each resident's hour goals (soft constraint)"""
        constraints = []

        for resident in self.residents:
            if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                continue

            # Calculate total hours for this resident
            total_hours = 0
            for day in self.days:
                for shift in self.shifts_by_day[day]:
                    if (day, shift, resident) in self.assignments:
                        duration = shift.duration(resident.pgy_level)
                        total_hours += (
                            self.assignments[(day, shift, resident)] * duration
                        )

            # Create deviation variable
            deviation = self.model.NewIntVar(0, 1000, f"deviation_{resident.name}")

            # |total_hours - hours_goal| = deviation
            constraints.append(
                self.model.AddAbsEquality(deviation, total_hours - resident.hours_goal)
            )

            # Add to objective terms
            self.objective_terms.append(deviation)

        return constraints

    def _alternating_hospital_constraints(self) -> List[cp_model.Constraint]:
        """Prefer alternating between hospitals when working consecutive days"""
        constraints = []

        for day_idx, day in enumerate(self.days):
            if day_idx == 0:
                continue

            prev_day = self.days[day_idx - 1]

            for resident in self.residents:
                if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                    continue

                for hospital in self.hospital_system.hospitals:
                    # Get shifts at this hospital
                    current_hospital_shifts = [
                        s
                        for s in self.shifts_by_day[day]
                        if s.hospital.name == hospital.name
                    ]
                    prev_hospital_shifts = [
                        s
                        for s in self.shifts_by_day[prev_day]
                        if s.hospital.name == hospital.name
                    ]

                    if current_hospital_shifts and prev_hospital_shifts:
                        # Create violation variable
                        violation = self.model.NewBoolVar(
                            f"hospital_violation_{day.strftime('%Y-%m-%d')}_{resident.name}_{hospital.name}"
                        )

                        # Sum of assignments at this hospital on both days
                        hospital_assignments = sum(
                            self.assignments[(prev_day, shift, resident)]
                            for shift in prev_hospital_shifts
                            if (prev_day, shift, resident) in self.assignments
                        ) + sum(
                            self.assignments[(day, shift, resident)]
                            for shift in current_hospital_shifts
                            if (day, shift, resident) in self.assignments
                        )

                        # If working at same hospital both days, violation = 1
                        constraints.append(
                            self.model.Add(hospital_assignments >= 2).OnlyEnforceIf(
                                violation
                            )
                        )
                        constraints.append(
                            self.model.Add(hospital_assignments < 2).OnlyEnforceIf(
                                violation.Not()
                            )
                        )

                        # Add to objective terms
                        self.objective_terms.append(violation)

        return constraints

    def _time_off_constraints(self) -> List[cp_model.Constraint]:
        """Try to accommodate time-off requests (soft constraint)"""
        constraints = []

        for resident in self.residents:
            if not resident.requests_off:
                continue

            for request_date in resident.requests_off:
                # Check if the requested date is in our schedule
                if request_date in self.days:
                    # Sum of assignments for this resident on this day
                    day_assignments = sum(
                        self.assignments[(request_date, shift, resident)]
                        for shift in self.shifts_by_day[request_date]
                        if (request_date, shift, resident) in self.assignments
                    )

                    # Create violation variable
                    violation = self.model.NewBoolVar(
                        f"request_violation_{request_date.strftime('%Y-%m-%d')}_{resident.name}"
                    )

                    # If working on requested day off, violation = 1
                    constraints.append(
                        self.model.Add(day_assignments > 0).OnlyEnforceIf(violation)
                    )
                    constraints.append(
                        self.model.Add(day_assignments == 0).OnlyEnforceIf(
                            violation.Not()
                        )
                    )

                    # Add to objective terms
                    self.objective_terms.append(violation)

        return constraints

    def _circadian_rhythm_constraints(self) -> List[cp_model.Constraint]:
        """Try to minimize circadian rhythm disruption (soft constraint)"""
        constraints = []

        for day_idx, day in enumerate(self.days):
            if day_idx < 2:
                continue

            prev_day = self.days[day_idx - 1]
            prev_prev_day = self.days[day_idx - 2]

            for resident in self.residents:
                if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                    continue

                # Check for disruptive patterns (e.g., 7AM -> 4PM -> 7AM)
                for shift in self.shifts_by_day[day]:
                    if (day, shift, resident) not in self.assignments:
                        continue

                    start_hour = shift.start_time.hour  # Now using time object

                    for prev_shift in self.shifts_by_day[prev_day]:
                        if (prev_day, prev_shift, resident) not in self.assignments:
                            continue

                        prev_start_hour = prev_shift.start_time.hour

                        for prev_prev_shift in self.shifts_by_day[prev_prev_day]:
                            if (
                                prev_prev_day,
                                prev_prev_shift,
                                resident,
                            ) not in self.assignments:
                                continue

                            prev_prev_start_hour = prev_prev_shift.start_time.hour

                            # Check for flip-flopping pattern
                            if (
                                prev_prev_start_hour == 7
                                and prev_start_hour >= 16
                                and start_hour == 7
                            ):
                                # Create violation variable
                                violation = self.model.NewBoolVar(
                                    f"rhythm_violation_{day.strftime('%Y-%m-%d')}_{resident.name}_flipflop"
                                )

                                # If all three shifts are assigned, violation = 1
                                constraints.append(
                                    self.model.Add(
                                        self.assignments[
                                            (prev_prev_day, prev_prev_shift, resident)
                                        ]
                                        + self.assignments[
                                            (prev_day, prev_shift, resident)
                                        ]
                                        + self.assignments[(day, shift, resident)]
                                        >= 3
                                    ).OnlyEnforceIf(violation)
                                )
                                constraints.append(
                                    self.model.Add(
                                        self.assignments[
                                            (prev_prev_day, prev_prev_shift, resident)
                                        ]
                                        + self.assignments[
                                            (prev_day, prev_shift, resident)
                                        ]
                                        + self.assignments[(day, shift, resident)]
                                        < 3
                                    ).OnlyEnforceIf(violation.Not())
                                )

                                # Add to objective terms
                                self.objective_terms.append(violation)

        return constraints

    def apply_constraints(
        self, constraint_specs: Optional[List[ConstraintSpec]] = None
    ) -> Dict[str, List[cp_model.Constraint]]:
        """Apply constraints to the model"""
        if constraint_specs is None:
            constraint_specs = self.get_constraint_specs()

        applied_constraints = {}
        for spec in constraint_specs:
            if spec.enabled:
                constraints = spec.constraint_func()
                applied_constraints[spec.name] = constraints

        return applied_constraints

    def solve(self, enabled_constraints: Optional[List[str]] = None) -> Optional[Dict]:
        """Solve the scheduling problem"""
        # Get constraint specs and filter if needed
        constraint_specs = self.get_constraint_specs()
        if enabled_constraints is not None:
            constraint_specs = [
                spec for spec in constraint_specs if spec.name in enabled_constraints
            ]

        # Apply constraints
        applied_constraints = self.apply_constraints(constraint_specs)

        # Set objective if we have soft constraints
        if self.objective_terms:
            self.model.Minimize(sum(self.objective_terms))

        # Set solver parameters
        self.solver.parameters.random_seed = random.randint(0, 1000000)
        self.solver.parameters.max_time_in_seconds = 300

        # Solve the model
        status = self.solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self._extract_solution()
        else:
            return None

    def _extract_solution(self) -> Dict:
        """Extract the solution from the solver"""
        schedule = {}

        for day in self.days:
            schedule[day] = {}
            for shift in self.shifts_by_day[day]:
                for resident in self.residents:
                    if (day, shift, resident) in self.assignments:
                        if (
                            self.solver.Value(self.assignments[(day, shift, resident)])
                            == 1
                        ):
                            schedule[day][shift] = resident
                            break

        return schedule


def create_schedule(
    residents_data,
    shift_templates_data,
    start_date: date,
    end_date: date,
    hospital_system,
):
    """Create a schedule using the CP-SAT solver"""
    # Create domain objects
    residents = [Resident(**r) for r in residents_data]

    # Create shift templates and generate actual shifts for the date range
    shift_templates = [ShiftTemplate(**s) for s in shift_templates_data]
    shifts = generate_shifts_for_date_range(shift_templates, start_date, end_date)

    # Generate list of days
    days = []
    current_date = start_date
    while current_date <= end_date:
        days.append(current_date)
        current_date += timedelta(days=1)

    # Create the schedule model
    model = ScheduleModel(
        residents=residents, shifts=shifts, days=days, hospital_system=hospital_system
    )

    # Solve with all constraints
    schedule = model.solve()

    return schedule
