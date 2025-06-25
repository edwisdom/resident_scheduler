import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from base.objects import Hospital, HospitalSystem, PGYLevel, Resident, ServiceType, Team
from base.shift import Shift


@dataclass
class ScheduleModel:
    """Represents the scheduling problem model for the CP-SAT solver"""

    residents: List[Resident]
    shifts: List[Shift]
    days: List[date]
    hospital_system: HospitalSystem

    # Maps for efficient lookups
    residents_by_pgy: Dict[PGYLevel, List[Resident]] = field(init=False)
    shifts_by_day: Dict[datetime, List[Shift]] = field(init=False)
    shifts_by_team: Dict[Team, List[Shift]] = field(init=False)
    shifts_by_hospital: Dict[Hospital, List[Shift]] = field(init=False)

    # CP-SAT model components
    model: cp_model.CpModel = field(init=False)
    solver: cp_model.CpSolver = field(init=False)
    assignments: Dict[Tuple[datetime, Shift, Resident], cp_model.BoolVar] = field(
        init=False
    )

    def __post_init__(self):
        # Initialize the CP-SAT model
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

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

        # Group shifts by day
        self.shifts_by_day = {}
        for day in self.days:
            self.shifts_by_day[day] = [
                s for s in self.shifts if s.day.value == day.strftime("%A")[:1].upper()
            ]

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

        # Only create variables for eligible residents (not off-service or on vacation)
        eligible_residents = [
            r
            for r in self.residents
            if r.service_type not in [ServiceType.OFF_SERVICE, ServiceType.VACATION]
        ]

        for day in self.days:
            for shift in self.shifts_by_day[day]:
                for resident in eligible_residents:
                    # Create a unique key for this assignment
                    key = (day, shift, resident)
                    # Create a binary variable (0 or 1) for this assignment
                    self.assignments[key] = self.model.NewBoolVar(
                        f"assign_{day.strftime('%Y-%m-%d')}_{shift.code}_{resident.name}"
                    )

    def add_hard_constraints(self):
        """Add all hard constraints to the model"""
        self._add_shift_assignment_constraints()
        self._add_resident_daily_constraints()
        self._add_duty_hour_constraints()
        self._add_team_constraints()
        self._add_rest_period_constraints()
        self._add_day_off_constraints()

    def _add_shift_assignment_constraints(self):
        """Each mandatory shift must be assigned to exactly one resident"""
        for day in self.days:
            for shift in self.shifts_by_day[day]:
                if shift.is_mandatory:
                    # Sum of all assignments for this shift must equal 1
                    self.model.Add(
                        sum(
                            self.assignments[(day, shift, resident)]
                            for resident in self.residents
                            if (day, shift, resident) in self.assignments
                        )
                        == 1
                    )

    def _add_resident_daily_constraints(self):
        """Each resident can only work one shift per day"""
        for day in self.days:
            for resident in self.residents:
                if resident.service_type in [ServiceType.ED, ServiceType.PEDS]:
                    # Sum of all assignments for this resident on this day must be <= 1
                    self.model.Add(
                        sum(
                            self.assignments[(day, shift, resident)]
                            for shift in self.shifts_by_day[day]
                            if (day, shift, resident) in self.assignments
                        )
                        <= 1
                    )

    def _add_duty_hour_constraints(self):
        """Enforce duty hour constraints"""
        # 1. No more than 12 continuous scheduled hours
        self._add_continuous_hours_constraint()

        # 2. No more than 60 scheduled hours per week
        self._add_weekly_hours_constraint()

    def _add_continuous_hours_constraint(self):
        """No resident can work more than 12 continuous hours"""
        # This is complex to model directly, so we'll use a simplified approach
        # For each day, ensure that if a resident works a shift, they don't work
        # another shift that would exceed 12 hours of continuous work

        # Group shifts by start time for each day
        for day in self.days:
            shifts_by_start_time = {}
            for shift in self.shifts_by_day[day]:
                start_hour = shift.start_time.hour
                if start_hour not in shifts_by_start_time:
                    shifts_by_start_time[start_hour] = []
                shifts_by_start_time[start_hour].append(shift)

            # For each resident
            for resident in self.residents:
                if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                    continue

                # For each possible shift start time
                for start_hour, shifts in shifts_by_start_time.items():
                    # Find all shifts that would overlap with this start time
                    overlapping_shifts = []
                    for other_start_hour, other_shifts in shifts_by_start_time.items():
                        # If the other shift starts within 12 hours of this shift
                        if (other_start_hour - start_hour) % 24 < 12:
                            overlapping_shifts.extend(other_shifts)

                    # If there are overlapping shifts, ensure the resident doesn't work more than one
                    if len(overlapping_shifts) > 1:
                        self.model.Add(
                            sum(
                                self.assignments[(day, shift, resident)]
                                for shift in overlapping_shifts
                                if (day, shift, resident) in self.assignments
                            )
                            <= 1
                        )

    def _add_weekly_hours_constraint(self):
        """No resident can work more than 60 hours per week"""
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
                            # Get shift duration for this resident's PGY level
                            duration = shift.duration(resident.pgy_level)
                            # Add to total hours if assigned
                            total_hours += (
                                self.assignments[(day, shift, resident)] * duration
                            )

                # Ensure total hours doesn't exceed 60
                self.model.Add(total_hours <= 60)

    def _add_team_constraints(self):
        """Enforce team-specific constraints"""
        # Red team (R) must be staffed by PGY-3s
        for day in self.days:
            for shift in self.shifts_by_team[Team.RED]:
                if (
                    day,
                    shift,
                    None,
                ) in self.assignments:  # Check if this shift exists for this day
                    # Sum of assignments for PGY-3 residents must equal 1
                    self.model.Add(
                        sum(
                            self.assignments[(day, shift, resident)]
                            for resident in self.residents_by_pgy[PGYLevel.PGY3]
                            if (day, shift, resident) in self.assignments
                        )
                        == 1
                    )

        # Green team (G) must be staffed by PGY-2s
        for day in self.days:
            for shift in self.shifts_by_team[Team.GREEN]:
                if (day, shift, None) in self.assignments:
                    self.model.Add(
                        sum(
                            self.assignments[(day, shift, resident)]
                            for resident in self.residents_by_pgy[PGYLevel.PGY2]
                            if (day, shift, resident) in self.assignments
                        )
                        == 1
                    )

        # Intern team (I) must be staffed by PGY-1s
        for day in self.days:
            for shift in self.shifts_by_team[Team.INTERN]:
                if (day, shift, None) in self.assignments:
                    self.model.Add(
                        sum(
                            self.assignments[(day, shift, resident)]
                            for resident in self.residents_by_pgy[PGYLevel.PGY1]
                            if (day, shift, resident) in self.assignments
                        )
                        == 1
                    )

        # Blue team (B) must have at least one PGY-1
        for day in self.days:
            for shift in self.shifts_by_team[Team.BLUE]:
                if (day, shift, None) in self.assignments:
                    self.model.Add(
                        sum(
                            self.assignments[(day, shift, resident)]
                            for resident in self.residents_by_pgy[PGYLevel.PGY1]
                            if (day, shift, resident) in self.assignments
                        )
                        >= 1
                    )

    def _add_rest_period_constraints(self):
        """Ensure residents have equivalent rest periods between shifts"""
        # For each resident and each day
        for day_idx, day in enumerate(self.days):
            if day_idx == 0:  # Skip first day
                continue

            prev_day = self.days[day_idx - 1]

            for resident in self.residents:
                if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                    continue

                # For each shift on the current day
                for shift in self.shifts_by_day[day]:
                    if (day, shift, resident) not in self.assignments:
                        continue

                    # Get shift duration
                    duration = shift.duration(resident.pgy_level)

                    # For each shift on the previous day
                    for prev_shift in self.shifts_by_day[prev_day]:
                        if (prev_day, prev_shift, resident) not in self.assignments:
                            continue

                        # Get previous shift duration
                        prev_duration = prev_shift.duration(resident.pgy_level)

                        # Calculate rest period
                        rest_period = 24 - prev_duration

                        # If rest period is less than the current shift duration, add constraint
                        if rest_period < duration:
                            # Resident cannot work both shifts
                            self.model.Add(
                                self.assignments[(prev_day, prev_shift, resident)]
                                + self.assignments[(day, shift, resident)]
                                <= 1
                            )

    def _add_day_off_constraints(self):
        """Ensure residents have at least one day off per week"""
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

                # Number of days in the week
                days_in_week = len(week_days)

                # Ensure at least one day off (assignments <= days_in_week - 1)
                self.model.Add(week_assignments <= days_in_week - 1)

    def add_soft_constraints(self):
        """Add all soft constraints to the model"""
        self._add_hour_goal_constraints()
        self._add_alternating_hospital_constraints()
        self._add_time_off_constraints()
        self._add_circadian_rhythm_constraints()

    def _add_hour_goal_constraints(self):
        """Try to meet each resident's hour goals"""
        # For each resident
        for resident in self.residents:
            if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                continue

            # Calculate total hours for this resident
            total_hours = 0
            for day in self.days:
                for shift in self.shifts_by_day[day]:
                    if (day, shift, resident) in self.assignments:
                        # Get shift duration for this resident's PGY level
                        duration = shift.duration(resident.pgy_level)
                        # Add to total hours if assigned
                        total_hours += (
                            self.assignments[(day, shift, resident)] * duration
                        )

            # Create a variable for the deviation from the goal
            deviation = self.model.NewIntVar(0, 1000, f"deviation_{resident.name}")

            # |total_hours - hours_goal| = deviation
            self.model.AddAbsEquality(deviation, total_hours - resident.hours_goal)

            # Add to objective: minimize deviation
            self.objective_terms.append(deviation)

    def _add_alternating_hospital_constraints(self):
        """Prefer alternating between hospitals when working consecutive days"""
        # For each resident and each day (except the first)
        for day_idx, day in enumerate(self.days):
            if day_idx == 0:  # Skip first day
                continue

            prev_day = self.days[day_idx - 1]

            for resident in self.residents:
                if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                    continue

                # For each hospital
                for hospital in self.hospital_system.hospitals:
                    # Get shifts at this hospital on the current day
                    current_hospital_shifts = [
                        s
                        for s in self.shifts_by_day[day]
                        if s.hospital.name == hospital.name
                    ]

                    # Get shifts at this hospital on the previous day
                    prev_hospital_shifts = [
                        s
                        for s in self.shifts_by_day[prev_day]
                        if s.hospital.name == hospital.name
                    ]

                    # If the resident worked at this hospital on the previous day
                    # and is working at this hospital on the current day, add a penalty
                    if current_hospital_shifts and prev_hospital_shifts:
                        # Create a binary variable for this violation
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

                        # If hospital_assignments >= 2, then violation = 1
                        self.model.Add(hospital_assignments >= 2).OnlyEnforceIf(
                            violation
                        )
                        self.model.Add(hospital_assignments < 2).OnlyEnforceIf(
                            violation.Not()
                        )

                        # Add to objective: minimize violations
                        self.objective_terms.append(violation)

    def _add_time_off_constraints(self):
        """Try to accommodate time-off requests"""
        # For each resident
        for resident in self.residents:
            if not resident.requests_off:
                continue

            # For each requested day off
            for request_date in resident.requests_off:
                # Find the closest day in our schedule
                closest_day = min(self.days, key=lambda d: abs((d - request_date).days))

                # If the closest day is in our schedule
                if abs((closest_day - request_date).days) <= 7:  # Within a week
                    # Sum of assignments for this resident on this day
                    day_assignments = sum(
                        self.assignments[(closest_day, shift, resident)]
                        for shift in self.shifts_by_day[closest_day]
                        if (closest_day, shift, resident) in self.assignments
                    )

                    # Create a binary variable for this violation
                    violation = self.model.NewBoolVar(
                        f"request_violation_{closest_day.strftime('%Y-%m-%d')}_{resident.name}"
                    )

                    # If day_assignments > 0, then violation = 1
                    self.model.Add(day_assignments > 0).OnlyEnforceIf(violation)
                    self.model.Add(day_assignments == 0).OnlyEnforceIf(violation.Not())

                    # Add to objective: minimize violations
                    self.objective_terms.append(violation)

    def _add_circadian_rhythm_constraints(self):
        """Try to minimize circadian rhythm disruption"""
        # For each resident and each day (except the first two)
        for day_idx, day in enumerate(self.days):
            if day_idx < 2:  # Skip first two days
                continue

            prev_day = self.days[day_idx - 1]
            prev_prev_day = self.days[day_idx - 2]

            for resident in self.residents:
                if resident.service_type not in [ServiceType.ED, ServiceType.PEDS]:
                    continue

                # For each shift on the current day
                for shift in self.shifts_by_day[day]:
                    if (day, shift, resident) not in self.assignments:
                        continue

                    # Get shift start hour
                    start_hour = shift.start_time.hour

                    # For each shift on the previous day
                    for prev_shift in self.shifts_by_day[prev_day]:
                        if (prev_day, prev_shift, resident) not in self.assignments:
                            continue

                        # Get previous shift start hour
                        prev_start_hour = prev_shift.start_time.hour

                        # For each shift on the day before the previous day
                        for prev_prev_shift in self.shifts_by_day[prev_prev_day]:
                            if (
                                prev_prev_day,
                                prev_prev_shift,
                                resident,
                            ) not in self.assignments:
                                continue

                            # Get shift start hour
                            prev_prev_start_hour = prev_prev_shift.start_time.hour

                            # Check for disruptive patterns
                            # 1. 7AM -> 4PM -> 7AM (flip-flopping)
                            if (
                                prev_prev_start_hour == 7
                                and prev_start_hour >= 16
                                and start_hour == 7
                            ):
                                # Create a binary variable for this violation
                                violation = self.model.NewBoolVar(
                                    f"rhythm_violation_{day.strftime('%Y-%m-%d')}_{resident.name}_flipflop"
                                )

                                # If all three shifts are assigned, then violation = 1
                                self.model.Add(
                                    self.assignments[
                                        (prev_prev_day, prev_prev_shift, resident)
                                    ]
                                    + self.assignments[(prev_day, prev_shift, resident)]
                                    + self.assignments[(day, shift, resident)]
                                    >= 3
                                ).OnlyEnforceIf(violation)

                                self.model.Add(
                                    self.assignments[
                                        (prev_prev_day, prev_prev_shift, resident)
                                    ]
                                    + self.assignments[(prev_day, prev_shift, resident)]
                                    + self.assignments[(day, shift, resident)]
                                    < 3
                                ).OnlyEnforceIf(violation.Not())

                                # Add to objective: minimize violations
                                self.objective_terms.append(violation)

    def solve(self):
        """Solve the scheduling problem"""
        # Set solver parameters for randomization
        self.solver.parameters.random_seed = random.randint(0, 1000000)

        # Set time limit (in seconds)
        self.solver.parameters.max_time_in_seconds = 300  # 5 minutes

        # Set the objective to minimize the sum of all objective terms
        self.model.Minimize(sum(self.objective_terms))

        # Solve the model
        status = self.solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self._extract_solution()
        else:
            return None

    def _extract_solution(self):
        """Extract the solution from the solver"""
        schedule = {}

        # For each day
        for day in self.days:
            schedule[day] = {}

            # For each shift on this day
            for shift in self.shifts_by_day[day]:
                # Find the resident assigned to this shift
                for resident in self.residents:
                    if (day, shift, resident) in self.assignments:
                        if (
                            self.solver.Value(self.assignments[(day, shift, resident)])
                            == 1
                        ):
                            schedule[day][shift] = resident
                            break

        return schedule


def create_schedule(residents_data, shifts_data, days, hospital_system):
    """Create a schedule using the CP-SAT solver"""
    # Create domain objects
    residents = [Resident(**r) for r in residents_data]
    shifts = [Shift(**s) for s in shifts_data]

    # Create the schedule model
    model = ScheduleModel(
        residents=residents, shifts=shifts, days=days, hospital_system=hospital_system
    )

    # Add constraints
    model.add_hard_constraints()
    model.add_soft_constraints()

    # Solve the model
    schedule = model.solve()

    return schedule
