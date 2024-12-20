from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
from enums import BookCategory, Department, YearLevel, YEAR_LEVEL_LIMITS

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Admin actions tracking
    created_students = relationship("Student", backref="created_by")
    created_books = relationship("Book", back_populates="admin")
    managed_borrows = relationship("BorrowRecord", backref="managed_by")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String, index=True)
    student_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    department = Column(Enum(Department), index=True)
    year_level = Column(Enum(YearLevel), index=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    borrow_history = relationship("BorrowRecord", back_populates="student")

    @property
    def borrowed_books_count(self):
        return sum(1 for record in self.borrow_history if not record.return_date)

    @property
    def has_overdue_books(self):
        current_time = datetime.utcnow()
        return any(
            not record.return_date and record.due_date < current_time
            for record in self.borrow_history
        )

    @property
    def max_books_allowed(self):
        return YEAR_LEVEL_LIMITS.get(self.year_level, 2)

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    isbn = Column(String, unique=True, index=True)
    category = Column(Enum(BookCategory))
    description = Column(String, nullable=True)
    quantity = Column(Integer, default=1)
    available_quantity = Column(Integer)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    admin = relationship("Admin", back_populates="created_books")
    borrow_records = relationship("BorrowRecord", back_populates="book")

    @property
    def is_borrowed(self):
        return self.available_quantity == 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.available_quantity = kwargs.get('quantity', 1)

class BorrowRecord(Base):
    __tablename__ = "borrow_records"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    admin_id = Column(Integer, ForeignKey("admins.id"))
    borrow_date = Column(DateTime, default=datetime.utcnow)
    return_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime)
    book = relationship("Book", back_populates="borrow_records")
    student = relationship("Student", back_populates="borrow_history")

    @property
    def is_overdue(self):
        return not self.return_date and self.due_date < datetime.utcnow()
    
    @property
    def is_returned(self):
        return self.return_date is not None
