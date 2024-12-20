from enum import Enum

class BookCategory(str, Enum):
    FICTION = "Fiction"
    NON_FICTION = "Non-Fiction"
    SCIENCE = "Science"
    TECHNOLOGY = "Technology"
    HISTORY = "History"
    LITERATURE = "Literature"
    REFERENCE = "Reference"
    OTHER = "Other"

class Department(str, Enum):
    COMPUTER_SCIENCE = "Computer Science"
    ENGINEERING = "Engineering"
    BUSINESS = "Business"
    ARTS = "Arts"
    SCIENCE = "Science"
    MEDICINE = "Medicine"
    LAW = "Law"
    OTHER = "Other"

class YearLevel(int, Enum):
    FIRST_YEAR = 1
    SECOND_YEAR = 2
    THIRD_YEAR = 3
    FOURTH_YEAR = 4
    GRADUATE = 5

# Borrowing limits configuration
YEAR_LEVEL_LIMITS = {
    YearLevel.FIRST_YEAR: 2,
    YearLevel.SECOND_YEAR: 3,
    YearLevel.THIRD_YEAR: 4,
    YearLevel.FOURTH_YEAR: 5,
    YearLevel.GRADUATE: 6
}
