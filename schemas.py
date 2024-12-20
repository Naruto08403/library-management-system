from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from models import BookCategory, Department, YearLevel

class AdminBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str

class AdminCreate(AdminBase):
    password: str

class Admin(AdminBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class StudentBase(BaseModel):
    student_id: str
    fullname: str
    email: EmailStr
    department: Department
    # year_level: YearLevel
    phone: Optional[str] = None
    is_active: bool = True

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    student_id: Optional[str] = None
    fullname: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[Department] = None
    # year_level: Optional[YearLevel] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class Student(StudentBase):
    id: int
    is_active: bool
    created_at: datetime
    admin_id: Optional[int]
    borrowed_books_count: int
    max_books_allowed: int
    has_overdue_books: bool

    class Config:
        from_attributes = True

class StudentResponse(StudentBase):
    id: int
    borrowed_books_count: int = 0

    class Config:
        from_attributes = True

class BookBase(BaseModel):
    title: str
    author: str
    isbn: str
    category: BookCategory
    description: Optional[str] = None
    quantity: int = 1

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    category: Optional[BookCategory] = None
    description: Optional[str] = None
    quantity: Optional[int] = None

class Book(BookBase):
    id: int
    is_borrowed: bool
    created_at: datetime
    admin_id: Optional[int]

    class Config:
        from_attributes = True

class BookResponse(BookBase):
    id: int
    # is_borrowed: bool
    available_quantity: int
    quantity: int

    class Config:
        from_attributes = True

# Borrow schemas
class BorrowBase(BaseModel):
    student_id: int
    book_id: int
    due_date: datetime
    notes: Optional[str] = None

class BorrowCreate(BorrowBase):
    pass

class BorrowUpdate(BaseModel):
    due_date: Optional[datetime] = None
    notes: Optional[str] = None

class BorrowReturn(BaseModel):
    borrow_id: int

class BorrowResponse(BaseModel):
    id: int
    student_id: int
    book_id: int
    borrow_date: datetime
    return_date: Optional[datetime] = None
    due_date: datetime
    notes: Optional[str] = None
    is_returned: bool
    is_overdue: bool
    book: BookResponse
    student: StudentResponse

    class Config:
        from_attributes = True

# Report schemas
class DateRangeFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class BorrowStats(BaseModel):
    total_borrows: int
    active_borrows: int
    overdue_borrows: int
    return_rate: float

class PopularBook(BaseModel):
    book_id: int
    title: str
    borrow_count: int

class ReportResponse(BaseModel):
    stats: BorrowStats
    popular_books: List[PopularBook]
    department_distribution: Dict[str, int]
    daily_borrows: List[Dict[str, Any]]

# Search and Filter Schemas
class BorrowHistoryFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    department: Optional[Department] = None
    category: Optional[BookCategory] = None
    is_returned: Optional[bool] = None
    is_overdue: Optional[bool] = None
    student_id: Optional[int] = None
    book_id: Optional[int] = None
    search_query: Optional[str] = None

class AdminStats(BaseModel):
    total_students_created: int
    total_books_added: int
    total_borrows_managed: int
    active_borrows: int
    overdue_books: int
    books_by_department: Dict[Department, int]
    borrows_by_year_level: Dict[YearLevel, int]

    class Config:
        from_attributes = True
