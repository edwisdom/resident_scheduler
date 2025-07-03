from pathlib import Path

import pandas as pd
import pytest

from formats.readers import read_shifts
from src.base.objects import DayOfWeek, Team


class TestReadShifts:
    def test_basic_shifts(self, tmp_path):
        """Test reading basic shifts from CSV"""
        # Create test data with all required day columns
        test_data = {
            "MONDAY": ["LR7", "LG1", ""],
            "TUESDAY": ["LR7", "LG1", "WR4"],
            "WEDNESDAY": ["", "LG1", "LIdw"],  # LIdw already includes day
            "THURSDAY": ["LR7", "LG1", ""],
            "FRIDAY": ["LR7", "LG1", ""],
            "SATURDAY": ["", "", ""],
            "SUNDAY": ["", "", ""],
        }

        df = pd.DataFrame(test_data)
        test_file = tmp_path / "test_shifts.csv"
        df.to_csv(test_file, index=False)

        # Read shifts
        shifts = read_shifts(test_file)

        # Should have 11 shifts (empty cells are skipped)
        assert len(shifts) == 11

        # Check a few specific shifts
        monday_shifts = [s for s in shifts if s.day == DayOfWeek.MONDAY]
        assert len(monday_shifts) == 2

        # Check that LIdw was parsed correctly (special case)
        lidw_shifts = [s for s in shifts if s.code == "m-L-I-14-W"]
        assert len(lidw_shifts) == 1
        assert lidw_shifts[0].day == DayOfWeek.WEDNESDAY
        assert lidw_shifts[0].hospital.name == "L"
        assert lidw_shifts[0].team == Team.INTERN

    def test_optional_shifts(self, tmp_path):
        """Test reading optional shifts (wrapped in parentheses)"""
        test_data = {
            "MONDAY": ["(LE11)", "LR7"],
            "TUESDAY": ["(WR4)", ""],
            "WEDNESDAY": ["", ""],
            "THURSDAY": ["", ""],
            "FRIDAY": ["", ""],
            "SATURDAY": ["", ""],
            "SUNDAY": ["", ""],
        }

        df = pd.DataFrame(test_data)
        test_file = tmp_path / "test_shifts.csv"
        df.to_csv(test_file, index=False)

        shifts = read_shifts(test_file)

        # Check optional shifts
        optional_shifts = [s for s in shifts if not s.is_mandatory]
        assert len(optional_shifts) == 2

        # Check codes
        codes = [s.code for s in shifts]
        assert "o-L-E-11-M" in codes  # (LE11) on Monday - 11 AM
        assert "o-W-R-16-T" in codes  # (WR4) on Tuesday - 4 PM

    def test_special_cases(self, tmp_path):
        """Test special cases LIdw and LB11w"""
        test_data = {
            "MONDAY": ["", ""],
            "TUESDAY": ["", ""],
            "WEDNESDAY": ["LIdw", "LB11w"],
            "THURSDAY": ["", ""],
            "FRIDAY": ["", ""],
            "SATURDAY": ["", ""],
            "SUNDAY": ["", ""],
        }

        df = pd.DataFrame(test_data)
        test_file = tmp_path / "test_shifts.csv"
        df.to_csv(test_file, index=False)

        shifts = read_shifts(test_file)

        assert len(shifts) == 2

        # Check LIdw
        lidw_shift = next(s for s in shifts if "I-14-W" in s.code)
        assert lidw_shift.day == DayOfWeek.WEDNESDAY
        assert lidw_shift.team == Team.INTERN

        # Check LB11w
        lb11w_shift = next(s for s in shifts if "B-14-W" in s.code)
        assert lb11w_shift.day == DayOfWeek.WEDNESDAY
        assert lb11w_shift.team == Team.BLUE

    def test_empty_csv(self, tmp_path):
        """Test CSV with all empty cells"""
        test_data = {day.to_full_str(): ["", "", ""] for day in DayOfWeek}

        df = pd.DataFrame(test_data)
        test_file = tmp_path / "test_shifts.csv"
        df.to_csv(test_file, index=False)

        shifts = read_shifts(test_file)
        assert len(shifts) == 0

    def test_invalid_columns(self, tmp_path):
        """Test CSV with wrong column names"""
        test_data = {
            "Mon": ["LR7"],  # Wrong column name
            "Tue": ["LG1"],
        }

        df = pd.DataFrame(test_data)
        test_file = tmp_path / "test_shifts.csv"
        df.to_csv(test_file, index=False)

        with pytest.raises(
            ValueError, match="Columns do not match DayOfWeek expectations"
        ):
            read_shifts(test_file)

    def test_invalid_shift_codes(self, tmp_path, capsys):
        """Test handling of invalid shift codes"""
        test_data = {day.to_full_str(): ["", "", ""] for day in DayOfWeek}
        test_data["MONDAY"] = ["LR7", "INVALID", "LG1"]  # Include invalid code

        df = pd.DataFrame(test_data)
        test_file = tmp_path / "test_shifts.csv"
        df.to_csv(test_file, index=False)

        shifts = read_shifts(test_file)

        # Should skip invalid code and continue with valid ones
        assert len(shifts) == 2  # LR7 and LG1

        # Check that warning was printed
        captured = capsys.readouterr()
        assert "Warning: Could not parse shift code" in captured.out

    def test_all_day_columns_required(self, tmp_path):
        """Test that all 7 day columns are required"""
        # Missing Sunday column
        test_data = {
            day.to_full_str(): ["LR7"] for day in DayOfWeek if day != DayOfWeek.SUNDAY
        }

        df = pd.DataFrame(test_data)
        test_file = tmp_path / "test_shifts.csv"
        df.to_csv(test_file, index=False)

        with pytest.raises(
            ValueError, match="Columns do not match DayOfWeek expectations"
        ):
            read_shifts(test_file)

    def test_shift_properties(self, tmp_path):
        """Test that shift properties are set correctly"""
        test_data = {day.to_full_str(): [""] for day in DayOfWeek}
        test_data["MONDAY"] = ["LR7"]  # Monday 7AM Red team at L hospital

        df = pd.DataFrame(test_data)
        test_file = tmp_path / "test_shifts.csv"
        df.to_csv(test_file, index=False)

        shifts = read_shifts(test_file)

        assert len(shifts) == 1
        shift = shifts[0]

        assert shift.hospital.name == "L"
        assert shift.team == Team.RED
        assert shift.day == DayOfWeek.MONDAY
        assert shift.start_time.hour == 7
        assert shift.is_mandatory == True
        assert shift.code == "m-L-R-07-M"


if __name__ == "__main__":
    # Run a simple test if executed directly
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        test = TestReadShifts()
        print("Running basic test...")
        test.test_basic_shifts(Path(tmp_dir))
        print("✓ Basic test passed!")

        print("Running special cases test...")
        test.test_special_cases(Path(tmp_dir))
        print("✓ Special cases test passed!")

        print("All tests passed!")
        print("All tests passed!")
