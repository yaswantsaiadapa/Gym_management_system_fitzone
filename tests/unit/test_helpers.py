# tests/unit/test_helpers.py
from datetime import date
import pytest

# import from your project package; adjust if your package name differs
from app.utils import helpers


def test_calculate_expiry_date_simple_month_add():
    # adding 1 month to mid-month should simply increase month
    start = date(2023, 1, 15)
    expiry = helpers.calculate_expiry_date(start, months=1)
    assert expiry.year == 2023
    assert expiry.month == 2
    assert expiry.day == 15


def test_calculate_expiry_date_year_rollover():
    # December + 1 month should go to next year January
    start = date(2023, 12, 5)
    expiry = helpers.calculate_expiry_date(start, months=1)
    assert expiry.year == 2024
    assert expiry.month == 1
    assert expiry.day == 5


def test_calculate_bmi_standard():
    # 70 kg, 175 cm -> BMI ~ 22.9 (rounded to 1 decimal)
    bmi = helpers.calculate_bmi(weight_kg=70, height_cm=175)
    assert isinstance(bmi, float)
    assert bmi == pytest.approx(22.9, rel=1e-3)


def test_calculate_bmi_invalid_inputs():
    # invalid heights or weights should return None (or raise — adjust if your implementation differs)
    assert helpers.calculate_bmi(weight_kg=0, height_cm=175) is None
    assert helpers.calculate_bmi(weight_kg=70, height_cm=0) is None
    assert helpers.calculate_bmi(weight_kg=-5, height_cm=175) is None


def test_get_bmi_category():
    assert helpers.get_bmi_category(None) == "Unknown"
    assert helpers.get_bmi_category(17.0) == "Underweight"
    assert helpers.get_bmi_category(22.0) == "Normal weight"
    assert helpers.get_bmi_category(27.0) == "Overweight"
    assert helpers.get_bmi_category(32.0) == "Obese"

