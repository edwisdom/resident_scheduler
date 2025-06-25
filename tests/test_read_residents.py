import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from src.adapters import read_residents
from src.base.objects import PGYLevel, ServiceType


def create_test_csv(data: list[dict], filename: Path) -> None:
    """Helper function to create a test CSV file"""
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)


def test_read_residents_basic():
    """Test basic reading of residents without date requests"""
    test_data = [
        {
            "Resident": "John Doe",
            "PGY": 1,
            "Service": "ED",
            "Hours/Block Goal": 216,
            "Requests": "",
        },
        {
            "Resident": "Jane Smith",
            "PGY": 2,
            "Service": "Off-Service",
            "Hours/Block Goal": 190,
            "Requests": "",
        },
        {
            "Resident": "Bob Wilson",
            "PGY": 3,
            "Service": "Peds",
            "Hours/Block Goal": 170,
            "Requests": "",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_path = Path(f.name)

    try:
        create_test_csv(test_data, temp_path)
        residents = read_residents(temp_path)

        assert len(residents) == 3

        # Check first resident
        assert residents[0].name == "John Doe"
        assert residents[0].pgy_level == PGYLevel.PGY1
        assert residents[0].service_type == ServiceType.ED
        assert residents[0].hours_goal == 216
        assert residents[0].requests_off == []

        # Check second resident
        assert residents[1].name == "Jane Smith"
        assert residents[1].pgy_level == PGYLevel.PGY2
        assert residents[1].service_type == ServiceType.OFF_SERVICE
        assert residents[1].hours_goal == 190
        assert residents[1].requests_off == []

        # Check third resident
        assert residents[2].name == "Bob Wilson"
        assert residents[2].pgy_level == PGYLevel.PGY3
        assert residents[2].service_type == ServiceType.PEDS
        assert residents[2].hours_goal == 170
        assert residents[2].requests_off == []

    finally:
        temp_path.unlink()


def test_read_residents_with_single_date_request():
    """Test reading residents with single date requests"""
    test_data = [
        {
            "Resident": "Alice Brown",
            "PGY": 2,
            "Service": "ED",
            "Hours/Block Goal": 190,
            "Requests": "7/15/2024",
        }
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_path = Path(f.name)

    try:
        create_test_csv(test_data, temp_path)
        residents = read_residents(temp_path)

        assert len(residents) == 1
        assert residents[0].name == "Alice Brown"
        assert len(residents[0].requests_off) == 1
        assert residents[0].requests_off[0] == date(2024, 7, 15)

    finally:
        temp_path.unlink()


def test_read_residents_with_multiple_date_requests():
    """Test reading residents with multiple comma-separated date requests"""
    test_data = [
        {
            "Resident": "Charlie Davis",
            "PGY": 3,
            "Service": "Vacation",
            "Hours/Block Goal": 170,
            "Requests": "7/8/2024, 7/9/2024, 8/2/2024",
        }
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_path = Path(f.name)

    try:
        create_test_csv(test_data, temp_path)
        residents = read_residents(temp_path)

        assert len(residents) == 1
        assert residents[0].name == "Charlie Davis"
        assert len(residents[0].requests_off) == 3
        assert date(2024, 7, 8) in residents[0].requests_off
        assert date(2024, 7, 9) in residents[0].requests_off
        assert date(2024, 8, 2) in residents[0].requests_off

    finally:
        temp_path.unlink()


def test_read_residents_mixed_requests():
    """Test reading residents with mix of empty and filled date requests"""
    test_data = [
        {
            "Resident": "David Lee",
            "PGY": 1,
            "Service": "ED",
            "Hours/Block Goal": 216,
            "Requests": "",
        },
        {
            "Resident": "Emma White",
            "PGY": 2,
            "Service": "Peds",
            "Hours/Block Goal": 190,
            "Requests": "12/25/2024",
        },
        {
            "Resident": "Frank Green",
            "PGY": 3,
            "Service": "ED",
            "Hours/Block Goal": 150,
            "Requests": "1/1/2025, 1/2/2025",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_path = Path(f.name)

    try:
        create_test_csv(test_data, temp_path)
        residents = read_residents(temp_path)

        assert len(residents) == 3

        # First resident - no requests
        assert residents[0].name == "David Lee"
        assert residents[0].requests_off == []

        # Second resident - single request
        assert residents[1].name == "Emma White"
        assert len(residents[1].requests_off) == 1
        assert residents[1].requests_off[0] == date(2024, 12, 25)

        # Third resident - multiple requests
        assert residents[2].name == "Frank Green"
        assert len(residents[2].requests_off) == 2
        assert date(2025, 1, 1) in residents[2].requests_off
        assert date(2025, 1, 2) in residents[2].requests_off

    finally:
        temp_path.unlink()


def test_read_residents_invalid_date_handling(capsys):
    """Test that invalid dates are handled gracefully with warnings"""
    test_data = [
        {
            "Resident": "Grace Kim",
            "PGY": 1,
            "Service": "ED",
            "Hours/Block Goal": 216,
            "Requests": "7/32/2024, 13/1/2024, 7/15/2024",  # Two invalid, one valid
        }
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_path = Path(f.name)

    try:
        create_test_csv(test_data, temp_path)
        residents = read_residents(temp_path)

        # Should still create the resident
        assert len(residents) == 1
        assert residents[0].name == "Grace Kim"

        # Should only have the valid date
        assert len(residents[0].requests_off) == 1
        assert residents[0].requests_off[0] == date(2024, 7, 15)

        # Should have printed warnings
        captured = capsys.readouterr()
        assert "Warning: Could not parse date" in captured.out
        assert "7/32/2024" in captured.out
        assert "13/1/2024" in captured.out

    finally:
        temp_path.unlink()


def test_read_residents_nan_requests():
    """Test handling of NaN values in requests column"""
    # Create a DataFrame with actual NaN values
    df = pd.DataFrame(
        [
            {
                "Resident": "Henry Jones",
                "PGY": 2,
                "Service": "ED",
                "Hours/Block Goal": 190,
                "Requests": pd.NA,  # Explicit NaN
            }
        ]
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_path = Path(f.name)

    try:
        df.to_csv(temp_path, index=False)
        residents = read_residents(temp_path)

        assert len(residents) == 1
        assert residents[0].name == "Henry Jones"
        assert residents[0].requests_off == []

    finally:
        temp_path.unlink()


def test_all_service_types():
    """Test that all service types are handled correctly"""
    test_data = [
        {
            "Resident": "A",
            "PGY": 1,
            "Service": "ED",
            "Hours/Block Goal": 216,
            "Requests": "",
        },
        {
            "Resident": "B",
            "PGY": 2,
            "Service": "Off-Service",
            "Hours/Block Goal": 190,
            "Requests": "",
        },
        {
            "Resident": "C",
            "PGY": 3,
            "Service": "Vacation",
            "Hours/Block Goal": 170,
            "Requests": "",
        },
        {
            "Resident": "D",
            "PGY": 1,
            "Service": "Peds",
            "Hours/Block Goal": 200,
            "Requests": "",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_path = Path(f.name)

    try:
        create_test_csv(test_data, temp_path)
        residents = read_residents(temp_path)

        assert len(residents) == 4
        assert residents[0].service_type == ServiceType.ED
        assert residents[1].service_type == ServiceType.OFF_SERVICE
        assert residents[2].service_type == ServiceType.VACATION
        assert residents[3].service_type == ServiceType.PEDS

    finally:
        temp_path.unlink()


def test_all_pgy_levels():
    """Test that all PGY levels are handled correctly"""
    test_data = [
        {
            "Resident": "PGY1",
            "PGY": 1,
            "Service": "ED",
            "Hours/Block Goal": 216,
            "Requests": "",
        },
        {
            "Resident": "PGY2",
            "PGY": 2,
            "Service": "ED",
            "Hours/Block Goal": 190,
            "Requests": "",
        },
        {
            "Resident": "PGY3",
            "PGY": 3,
            "Service": "ED",
            "Hours/Block Goal": 170,
            "Requests": "",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_path = Path(f.name)

    try:
        create_test_csv(test_data, temp_path)
        residents = read_residents(temp_path)

        assert len(residents) == 3
        assert residents[0].pgy_level == PGYLevel.PGY1
        assert residents[1].pgy_level == PGYLevel.PGY2
        assert residents[2].pgy_level == PGYLevel.PGY3

    finally:
        temp_path.unlink()
