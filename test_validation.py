import pytest
from datetime import datetime

def test_validate_name():
    from gui import validate_name
    assert validate_name("Иванов Иван Иванович") == True
    assert validate_name("Smith John") == True
    assert validate_name("123") == False
    assert validate_name("") == False

def test_validate_sex():
    from gui import validate_sex
    assert validate_sex("мужской") == True
    assert validate_sex("женский") == True
    assert validate_sex("male") == True
    assert validate_sex("female") == True
    assert validate_sex("unknown") == False

def test_validate_positive_integer():
    from gui import validate_positive_integer
    assert validate_positive_integer("100") == True
    assert validate_positive_integer("-10") == False
    assert validate_positive_integer("0") == False
    assert validate_positive_integer("abc") == False

def test_calculate_age():
    from gui import calculate_age
    today = datetime.today()
    test_date = today.replace(year=today.year - 30).strftime("%d.%m.%Y")
    assert calculate_age(test_date) == 30
    assert calculate_age("31.02.2020") == None  # Неверная дата