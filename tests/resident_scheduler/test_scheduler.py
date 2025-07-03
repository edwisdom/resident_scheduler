#!/usr/bin/env python3

from datetime import date, timedelta
from pathlib import Path

from base.objects import Hospital, HospitalSystem
from base.shift import generate_shifts_for_date_range
from formats.readers import read_residents, read_shifts
from resident_scheduler.scheduler import ScheduleModel


def test_scheduler():
    """Test the scheduler with actual test data"""
    print("Testing resident scheduler...")

    # Load test data
    test_data_dir = Path("test_data")
    residents = read_residents(test_data_dir / "residents.csv")
    shift_templates = read_shifts(test_data_dir / "weekly_shifts.csv")

    print(f"Loaded {len(residents)} residents")
    print(f"Loaded {len(shift_templates)} shift templates")

    # Filter to only active residents for this test
    active_residents = [r for r in residents if r.service_type.value in ["ED", "Peds"]]
    print(f"Found {len(active_residents)} active residents")

    # Create hospital system (L and W hospitals from the shift codes)
    hospital_system = HospitalSystem(
        name="Test Hospital System", hospitals=[Hospital(name="L"), Hospital(name="W")]
    )

    start_date = date(2024, 7, 8)
    end_date = date(2024, 8, 4)
    days = [start_date + timedelta(days=i) for i in range(28)]
    print(f"Scheduling for dates: {days[0]} to {days[-1]}")

    # Generate actual shifts from templates for the date range
    shifts = generate_shifts_for_date_range(shift_templates, start_date, end_date)
    print(f"Generated {len(shifts)} actual shifts for the date range")

    # Create and run the scheduler
    try:
        model = ScheduleModel(
            residents=active_residents,
            shifts=shifts,
            days=days,
            hospital_system=hospital_system,
        )

        print(f"Created {len(model.assignments)} assignment variables")

        # Get constraint specs and show what's enabled
        constraint_specs = model.get_constraint_specs()
        print(f"Enabled constraints: {[spec.name for spec in constraint_specs]}")

        # Apply constraints
        applied_constraints = model.apply_constraints(constraint_specs)

        # Solve with only the shift assignment constraint
        schedule = model.solve()

        if schedule:
            print("\n✅ Schedule found successfully!")

            # Analyze the schedule
            total_assignments = 0
            mandatory_shifts = [s for s in shifts if s.is_mandatory]

            for day in days:
                day_assignments = schedule.get(day, {})
                day_shift_count = len(day_assignments)
                total_assignments += day_shift_count
                print(
                    f"{day.strftime('%A %Y-%m-%d')}: {day_shift_count} shifts assigned"
                )

                # Show a few examples
                if day_assignments:
                    examples = list(day_assignments.items())[:3]
                    for shift, resident in examples:
                        print(
                            f"  {shift.code} -> {resident.name} (PGY-{resident.pgy_level.value})"
                        )
                    if len(day_assignments) > 3:
                        print(f"  ... and {len(day_assignments) - 3} more")

            print(f"\nTotal assignments: {total_assignments}")
            print(f"Total mandatory shifts: {len(mandatory_shifts)}")

            # Check if all mandatory shifts were assigned
            unassigned_shifts = []
            for day in days:
                day_assignments = schedule.get(day, {})
                for shift in shifts:
                    if (
                        shift.is_mandatory
                        and shift.date == day
                        and shift not in day_assignments
                    ):
                        unassigned_shifts.append((day, shift))

            if unassigned_shifts:
                print(
                    f"\n⚠️  {len(unassigned_shifts)} mandatory shifts were not assigned:"
                )
                for day, shift in unassigned_shifts[:5]:  # Show first 5
                    print(f"  {day}: {shift.code}")
                if len(unassigned_shifts) > 5:
                    print(f"  ... and {len(unassigned_shifts) - 5} more")
            else:
                print("\n✅ All mandatory shifts were assigned!")

        else:
            print("\n❌ No schedule found")
            print("This could mean:")
            print("- Not enough eligible residents")
            print("- Conflicting constraints")
            print("- Solver timeout")

            # Debug info
            print(f"\nDebug info:")
            print(f"- Active residents by PGY:")
            for pgy_level in [1, 2, 3]:
                count = len(
                    [r for r in active_residents if r.pgy_level.value == pgy_level]
                )
                print(f"  PGY-{pgy_level}: {count} residents")

            print(f"- Shifts by team:")
            from collections import Counter

            team_counts = Counter(
                shift.team.value for shift in shifts if shift.is_mandatory
            )
            for team, count in team_counts.items():
                print(f"  {team}: {count} shifts")

    except Exception as e:
        print(f"\n❌ Error running scheduler: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_scheduler()
