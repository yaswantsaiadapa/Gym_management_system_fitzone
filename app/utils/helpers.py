from datetime import date, timedelta
import re

def calculate_expiry_date(membership_date, months=1):
    """Calculate membership expiry date"""
    try:
        # Add one month to membership date
        if membership_date.month == 12:
            expiry_date = membership_date.replace(year=membership_date.year + 1, month=1)
        else:
            expiry_date = membership_date.replace(month=membership_date.month + months)
        return expiry_date
    except ValueError:
        # Handle cases where day doesn't exist in target month (e.g., Jan 31 -> Feb 31)
        next_month = membership_date.month + months
        year = membership_date.year
        
        if next_month > 12:
            year += next_month // 12
            next_month = next_month % 12
            if next_month == 0:
                next_month = 12
                year -= 1
        
        # Get the last day of the target month
        if next_month in [1, 3, 5, 7, 8, 10, 12]:
            last_day = 31
        elif next_month in [4, 6, 9, 11]:
            last_day = 30
        else:  # February
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                last_day = 29
            else:
                last_day = 28
        
        day = min(membership_date.day, last_day)
        return date(year, next_month, day)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate phone number format"""
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    # Check if it's 10 digits (adjust based on your region)
    return len(digits_only) >= 10

def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:,.2f}"

def calculate_age(birth_date):
    """Calculate age from birth date"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def calculate_bmi(weight_kg, height_cm):
    """Calculate BMI from weight and height"""
    if height_cm <= 0 or weight_kg <= 0:
        return None
    
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 1)

def get_bmi_category(bmi):
    """Get BMI category based on BMI value.

    Categories (WHO-style):
      - < 18.5 : 'Underweight'
      - 18.5 - <25 : 'Normal weight'
      - 25 - <30 : 'Overweight'
      - >=30 : 'Obese'
    """
    if bmi is None:
        return "Unknown"

    try:
        bmi_val = float(bmi)
    except Exception:
        # if not a number, treat as unknown
        return "Unknown"

    if bmi_val < 18.5:
        return "Underweight"
    elif bmi_val < 25:
        return "Normal weight"
    elif bmi_val < 30:
        return "Overweight"
    else:
        return "Obese"
