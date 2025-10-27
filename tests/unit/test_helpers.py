# tests/unit/test_helpers.py
from datetime import date
import pytest

from app.utils import helpers

def test_calculate_expiry_date_normal_month():
    start = date(2024, 3, 15)
    expiry = helpers.calculate_expiry_date(start, months=1)
    assert expiry.year == 2024
    assert expiry.month == 4
    assert expiry.day == 15

def test_calculate_expiry_date_year_rollover():
    start = date(2023, 12, 31)
    expiry = helpers.calculate_expiry_date(start, months=1)
    # Should move to next year January (or last valid day if logic adjusts)
    assert expiry.year >= 2024
    assert expiry.month in (1,)

def test_calculate_bmi_typical():
    # 70 kg, 175 cm => BMI ~ 22.9 rounded to 1 decimal per helpers implementation
    bmi = helpers.calculate_bmi(weight_kg=70, height_cm=175)
    assert isinstance(bmi, float)
    assert bmi == pytest.approx(22.9, rel=1e-3)

def test_calculate_bmi_invalid_values():
    # negative or zero dimensions should return None according to helpers
    assert helpers.calculate_bmi(0, 170) is None
    assert helpers.calculate_bmi(70, 0) is None
    assert helpers.calculate_bmi(-1, 170) is None

def test_get_bmi_category_defined_ranges():
    assert helpers.get_bmi_category(None) == "Unknown"
    assert helpers.get_bmi_category(16.0) == "Underweight"
    assert helpers.get_bmi_category(22.0) == "Normal weight"
    assert helpers.get_bmi_category(27.0) == "Overweight"
    assert helpers.get_bmi_category(32.0) == "Obese"
