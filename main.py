from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, asc, desc
from jose import JWTError, jwt
from passlib.context import CryptContext
import models
import database
import schemas
from enums import BookCategory, Department, YearLevel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from datetime import timezone

app = FastAPI(title="Library Management System")

# JWT Configuration
SECRET_KEY = "your-secret-key"  # Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={"admin": "Admin access"}
)

# Create tables
with database.engine.begin() as conn:
    models.Base.metadata.create_all(conn)

# Authentication functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def authenticate_admin(db: Session, username: str, password: str) -> Optional[models.Admin]:
    admin = db.query(models.Admin).filter(models.Admin.username == username).first()
    if not admin:
        return None
    if not verify_password(password, admin.hashed_password):
        return None
    return admin

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return payload
    except JWTError:
        return None

async def get_current_admin(
    request: Request,
    db: Session = Depends(database.get_db)
) -> Optional[models.Admin]:
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        return None
        
    try:
        token_data = verify_token(token.split(" ")[1])
        if not token_data:
            return None
            
        username = token_data.get("sub")
        if not username:
            return None
            
        admin = db.query(models.Admin).filter(
            models.Admin.username == username
        ).first()
        return admin
    except:
        return None

# Single admin creation endpoint
@app.post("/admin/create/", response_model=schemas.Admin)
async def create_admin(
    admin: schemas.AdminCreate,
    db: Session = Depends(database.get_db),
    
):
    # First check if any admin exists
    admin_exists = db.query(models.Admin).count() > 0

    # If admins exist, verify authentication
    '''if admin_exists:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to create additional admin accounts",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify the token and get current admin
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            current_admin = db.query(models.Admin).filter(models.Admin.username == username).first()
            if not current_admin:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )'''

    # Check if username already exists
    if db.query(models.Admin).filter(models.Admin.username == admin.username).first():
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Create new admin
    db_admin = models.Admin(
        username=admin.username,
        email=admin.email,
        full_name=admin.full_name,
        hashed_password=get_password_hash(admin.password)
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin

# Login endpoint
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    admin = authenticate_admin(db, form_data.username, form_data.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": admin.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Get current admin profile
@app.get("/admin/me/", response_model=schemas.Admin)
async def read_admin_me(
    current_admin: Optional[models.Admin] = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return current_admin

# Student management endpoints
@app.post("/students/", response_model=schemas.Student)
async def create_student(
    student: schemas.StudentCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )

    # Check if student_id already exists
    db_student = db.query(models.Student).filter(models.Student.student_id == student.student_id).first()
    if db_student:
        raise HTTPException(
            status_code=400,
            detail="Student ID already registered"
        )

    # Check if email already exists
    db_student = db.query(models.Student).filter(models.Student.email == student.email).first()
    if db_student:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Create new student
    db_student = models.Student(
        fullname=student.fullname,
        year=student.year,
        age=student.age,
        student_id=student.student_id,
        email=student.email,
        department=student.department,
        year_level=student.year_level,
        admin_id=current_admin.id,  # Set the admin_id
        is_active=True
    )
    
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@app.get("/students/", response_model=List[schemas.Student])
async def get_students(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )
    students = db.query(models.Student).offset(skip).limit(limit).all()
    return students

@app.get("/students/{student_id}", response_model=schemas.Student)
async def get_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

# Book management endpoints
@app.post("/api/books/", response_model=schemas.BookResponse)
async def create_book(
    book: schemas.BookCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Check if ISBN already exists
    db_book = db.query(models.Book).filter(models.Book.isbn == book.isbn).first()
    if db_book:
        raise HTTPException(status_code=400, detail="ISBN already registered")

    db_book = models.Book(**book.model_dump(), admin_id=current_admin.id)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@app.get("/api/books/{book_id}", response_model=schemas.BookResponse)
async def get_book(
    book_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    # Get book with borrow count
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    # Get borrow count
    borrow_count = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.book_id == book_id
    ).count()
    
    return {
        **book.__dict__,
        "borrow_count": borrow_count
    }

@app.put("/api/books/{book_id}", response_model=schemas.BookResponse)
async def update_book(
    book_id: int,
    book_update: schemas.BookUpdate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if ISBN is being updated and is unique
    if book_update.isbn and book_update.isbn != db_book.isbn:
        existing_book = db.query(models.Book).filter(
            models.Book.isbn == book_update.isbn
        ).first()
        if existing_book:
            raise HTTPException(
                status_code=400,
                detail="ISBN already registered"
            )

    # Handle quantity update
    if book_update.quantity is not None:
        if book_update.quantity < (db_book.quantity - db_book.available_quantity):
            raise HTTPException(
                status_code=400,
                detail="Cannot reduce quantity below number of borrowed books"
            )
        borrowed_count = db_book.quantity - db_book.available_quantity
        db_book.available_quantity = book_update.quantity - borrowed_count
        db_book.quantity = book_update.quantity

    # Update other book fields
    update_data = book_update.model_dump(exclude_unset=True)
    if 'quantity' in update_data:
        del update_data['quantity']  # Already handled above
    
    for field, value in update_data.items():
        setattr(db_book, field, value)

    db.commit()
    db.refresh(db_book)
    return db_book

@app.delete("/api/books/{book_id}")
async def delete_book(
    book_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    # Check if book exists
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    # Check if book has any active borrows
    active_borrow = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.book_id == book_id,
        models.BorrowRecord.return_date == None
    ).first()
    if active_borrow:
        raise HTTPException(status_code=400, detail="Cannot delete book with active borrows")
        
    # Delete book
    db.delete(db_book)
    db.commit()
    return {"message": "Book deleted successfully"}

@app.get("/api/books/", response_model=List[schemas.BookResponse])
async def list_books(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    category: Optional[BookCategory] = None,
    availability: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    # Base query
    query = db.query(models.Book)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                models.Book.title.ilike(f"%{search}%"),
                models.Book.author.ilike(f"%{search}%"),
                models.Book.isbn.ilike(f"%{search}%")
            )
        )
    if category:
        query = query.filter(models.Book.category == category)
    if availability:
        if availability == "available":
            query = query.filter(models.Book.available_quantity > 0)
        elif availability == "borrowed":
            query = query.filter(models.Book.available_quantity == 0)
            
    # Get books with borrow counts
    books = query.offset(skip).limit(limit).all()
    
    # Add borrow count to each book
    book_responses = []
    for book in books:
        borrow_count = db.query(models.BorrowRecord).filter(
            models.BorrowRecord.book_id == book.id
        ).count()
        book_dict = book.__dict__
        book_dict["borrow_count"] = borrow_count
        book_responses.append(book_dict)
    
    return book_responses

@app.post("/books/", response_model=schemas.Book)
async def create_book(
    book: schemas.BookCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )

    print(f"Creating book with admin_id: {current_admin.id}")  # Debug log

    # Check if ISBN already exists
    db_book = db.query(models.Book).filter(models.Book.isbn == book.isbn).first()
    if db_book:
        raise HTTPException(
            status_code=400,
            detail="ISBN already registered"
        )

    # Create new book
    db_book = models.Book(
        title=book.title,
        author=book.author,
        category=book.category,
        isbn=book.isbn,
        department=book.department,
        total_copies=book.total_copies,
        available_copies=book.total_copies,
        admin_id=current_admin.id,  # Explicitly set admin_id
        created_at=datetime.utcnow()
    )
    
    try:
        db.add(db_book)
        db.commit()
        db.refresh(db_book)
        print(f"Book created successfully with id: {db_book.id} and admin_id: {db_book.admin_id}")  # Debug log
        return db_book
    except Exception as e:
        print(f"Error creating book: {str(e)}")  # Debug log
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating book: {str(e)}")

@app.get("/books/", response_model=List[schemas.Book])
async def get_books(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )
    
    try:
        books = db.query(models.Book).offset(skip).limit(limit).all()
        print(f"Found {len(books)} books")  # Debug log
        for book in books:
            print(f"Book ID: {book.id}, Title: {book.title}, Admin ID: {book.admin_id}")  # Debug log
        return books
    except Exception as e:
        print(f"Error fetching books: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=f"Error fetching books: {str(e)}")

@app.get("/books/{book_id}", response_model=schemas.Book)
async def get_book(
    book_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.get("/books/category/{category}", response_model=List[schemas.Book])
async def get_books_by_category(
    category: BookCategory,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )
    books = db.query(models.Book).filter(models.Book.category == category).all()
    return books

# Book borrowing and returning endpoints
@app.post("/books/borrow/", response_model=schemas.BorrowResponse)
async def borrow_book(
    borrow_request: schemas.BorrowCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )

    # Get student and check status
    student = db.query(models.Student).filter(models.Student.id == borrow_request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not student.is_active:
        raise HTTPException(status_code=400, detail="Student is not active")

    # Check borrowing limits
    if student.current_borrowed_count >= student.max_books_allowed:
        raise HTTPException(
            status_code=400, 
            detail=f"Student has reached maximum borrowing limit ({student.max_books_allowed} books)"
        )

    # Check for overdue books
    if student.has_overdue_books:
        raise HTTPException(
            status_code=400,
            detail="Student has overdue books and cannot borrow more books until they are returned"
        )

    # Check if book exists and is available
    book = db.query(models.Book).filter(models.Book.id == borrow_request.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.available_quantity <= 0:
        raise HTTPException(status_code=400, detail="Book is not available")

    # Check if student already has this book
    existing_borrow = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.student_id == student.id,
        models.BorrowRecord.book_id == book.id,
        models.BorrowRecord.is_returned == False
    ).first()
    if existing_borrow:
        raise HTTPException(status_code=400, detail="Student already has this book")

    # Create borrow record
    borrow_record = models.BorrowRecord(
        book_id=book.id,
        student_id=student.id,
        admin_id=current_admin.id,
        due_date=borrow_request.due_date,
        is_returned=False
    )
    
    # Update book availability
    book.available_quantity -= 1

    db.add(borrow_record)
    db.commit()
    db.refresh(borrow_record)
    return borrow_record

@app.post("/books/return/", response_model=schemas.BorrowResponse)
async def return_book(
    return_request: schemas.BorrowReturn,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )

    # Get borrow record
    borrow_record = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.id == return_request.borrow_record_id
    ).first()
    if not borrow_record:
        raise HTTPException(status_code=404, detail="Borrow record not found")
    if borrow_record.is_returned:
        raise HTTPException(status_code=400, detail="Book already returned")

    # Update borrow record
    borrow_record.is_returned = True
    borrow_record.return_date = datetime.utcnow()

    # Update book availability
    book = db.query(models.Book).filter(models.Book.id == borrow_record.book_id).first()
    book.available_quantity += 1

    db.commit()
    db.refresh(borrow_record)
    return borrow_record

@app.get("/books/borrowed/", response_model=List[schemas.BorrowResponse])
async def get_borrowed_books(
    student_id: Optional[int] = None,
    department: Optional[Department] = None,
    category: Optional[BookCategory] = None,
    is_returned: Optional[bool] = None,
    is_overdue: Optional[bool] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )

    query = db.query(models.BorrowRecord)
    
    if student_id:
        query = query.filter(models.BorrowRecord.student_id == student_id)
    if department:
        query = query.join(models.Student).filter(models.Student.department == department)
    if category:
        query = query.join(models.Book).filter(models.Book.category == category)
    if is_returned is not None:
        query = query.filter(models.BorrowRecord.is_returned == is_returned)
    if is_overdue:
        current_time = datetime.utcnow()
        query = query.filter(
            models.BorrowRecord.due_date < current_time,
            models.BorrowRecord.is_returned == False
        )

    # Apply pagination
    query = query.offset(skip).limit(limit)

    return query.all()

@app.get("/books/overdue/", response_model=List[schemas.BorrowResponse])
async def get_overdue_books(
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )

    current_time = datetime.utcnow()
    overdue_books = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.due_date < current_time,
        models.BorrowRecord.is_returned == False
    ).all()
    
    return overdue_books

@app.get("/books/search/", response_model=List[schemas.BorrowResponse])
async def search_borrow_records(
    filters: schemas.BorrowHistoryFilter,
    skip: int = 0,
    limit: int = 10,
    sort_by: str = "borrow_date",
    sort_desc: bool = True,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )

    # Start with base query
    query = db.query(models.BorrowRecord)

    # Apply date filters
    if filters.start_date:
        query = query.filter(models.BorrowRecord.borrow_date >= filters.start_date)
    if filters.end_date:
        query = query.filter(models.BorrowRecord.borrow_date <= filters.end_date)

    # Apply status filters
    if filters.is_returned is not None:
        query = query.filter(models.BorrowRecord.is_returned == filters.is_returned)
    
    # Apply overdue filter
    if filters.is_overdue:
        current_time = datetime.utcnow()
        query = query.filter(
            models.BorrowRecord.due_date < current_time,
            models.BorrowRecord.is_returned == False
        )

    # Apply student and book filters
    if filters.student_id:
        query = query.filter(models.BorrowRecord.student_id == filters.student_id)
    if filters.book_id:
        query = query.filter(models.BorrowRecord.book_id == filters.book_id)

    # Apply department filter
    if filters.department:
        query = query.join(models.Student).filter(models.Student.department == filters.department)

    # Apply book category filter
    if filters.category:
        query = query.join(models.Book).filter(models.Book.category == filters.category)

    # Apply search query
    if filters.search_query:
        search = f"%{filters.search_query}%"
        query = query.join(models.Book).join(models.Student).filter(
            or_(
                models.Book.title.ilike(search),
                models.Student.fullname.ilike(search)
            )
        )

    # Apply sorting
    if sort_by == "borrow_date":
        query = query.order_by(desc(models.BorrowRecord.borrow_date) if sort_desc else asc(models.BorrowRecord.borrow_date))
    elif sort_by == "due_date":
        query = query.order_by(desc(models.BorrowRecord.due_date) if sort_desc else asc(models.BorrowRecord.due_date))
    elif sort_by == "return_date":
        query = query.order_by(desc(models.BorrowRecord.return_date) if sort_desc else asc(models.BorrowRecord.return_date))

    # Apply pagination
    query = query.offset(skip).limit(limit)

    return query.all()

@app.get("/students/{student_id}/borrow-stats/")
async def get_student_borrow_stats(
    student_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )

    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return {
        "current_borrowed": student.current_borrowed_count,
        "max_allowed": student.max_books_allowed,
        "has_overdue": student.has_overdue_books,
        "can_borrow": (
            student.current_borrowed_count < student.max_books_allowed
            and not student.has_overdue_books
        )
    }

# Student CRUD endpoints
@app.post("/api/students/", response_model=schemas.Student)
async def create_student(
    student: schemas.StudentCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    # Check if student_id already exists
    db_student = db.query(models.Student).filter(models.Student.student_id == student.student_id).first()
    if db_student:
        raise HTTPException(status_code=400, detail="Student ID already registered")
        
    # Check if email already exists
    db_student = db.query(models.Student).filter(models.Student.email == student.email).first()
    if db_student:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Create new student
    db_student = models.Student(
        **student.model_dump(),
        admin_id=current_admin.id,
    
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@app.get("/api/students/{student_id}", response_model=schemas.StudentResponse)
async def get_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    # Get student
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    # Get borrow statistics
    total_borrows = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.student_id == student_id
    ).count()
    
    active_borrows = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.student_id == student_id,
        models.BorrowRecord.return_date == None
    ).count()
    
    overdue_borrows = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.student_id == student_id,
        models.BorrowRecord.return_date == None,
        models.BorrowRecord.due_date < datetime.utcnow()
    ).count()
    
    return {
        **student.__dict__,
        "total_borrows": total_borrows,
        "active_borrows": active_borrows,
        "overdue_borrows": overdue_borrows
    }

@app.put("/api/students/{student_id}", response_model=schemas.Student)
async def update_student(
    student_id: int,
    student_update: schemas.StudentUpdate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    # Get existing student
    db_student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    # Check if student_id is being updated and if it conflicts
    if student_update.student_id and student_update.student_id != db_student.student_id:
        existing_student = db.query(models.Student).filter(
            models.Student.student_id == student_update.student_id
        ).first()
        if existing_student:
            raise HTTPException(status_code=400, detail="Student ID already registered")
            
    # Check if email is being updated and if it conflicts
    if student_update.email and student_update.email != db_student.email:
        existing_student = db.query(models.Student).filter(
            models.Student.email == student_update.email
        ).first()
        if existing_student:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Update student fields
    update_data = student_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_student, field, value)
        
    db.commit()
    db.refresh(db_student)
    return db_student

@app.delete("/api/students/{student_id}")
async def delete_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    # Check if student exists
    db_student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    # Check if student has any active borrows
    active_borrow = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.student_id == student_id,
        models.BorrowRecord.return_date == None
    ).first()
    if active_borrow:
        raise HTTPException(status_code=400, detail="Cannot delete student with active borrows")
        
    # Delete student
    db.delete(db_student)
    db.commit()
    return {"message": "Student deleted successfully"}

@app.get("/api/students/", response_model=List[schemas.StudentResponse])
async def list_students(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    department: Optional[Department] = None,
    year_level: Optional[YearLevel] = None,
    has_overdue: Optional[bool] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    # Base query
    query = db.query(models.Student)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                models.Student.fullname.ilike(f"%{search}%"),
                models.Student.student_id.ilike(f"%{search}%"),
                models.Student.email.ilike(f"%{search}%")
            )
        )
    if department:
        query = query.filter(models.Student.department == department)
    if year_level:
        query = query.filter(models.Student.year_level == year_level)
    if is_active is not None:
        query = query.filter(models.Student.is_active == is_active)
        
    # Get students
    students = query.offset(skip).limit(limit).all()
    
    # Add borrow statistics to each student
    student_responses = []
    for student in students:
        total_borrows = db.query(models.BorrowRecord).filter(
            models.BorrowRecord.student_id == student.id
        ).count()
        
        active_borrows = db.query(models.BorrowRecord).filter(
            models.BorrowRecord.student_id == student.id,
            models.BorrowRecord.return_date == None
        ).count()
        
        overdue_borrows = db.query(models.BorrowRecord).filter(
            models.BorrowRecord.student_id == student.id,
            models.BorrowRecord.return_date == None,
            models.BorrowRecord.due_date < datetime.utcnow()
        ).count()
        
        # Filter by overdue status if requested
        if has_overdue is not None:
            if has_overdue and overdue_borrows == 0:
                continue
            if not has_overdue and overdue_borrows > 0:
                continue
        
        student_dict = student.__dict__
        student_dict.update({
            "total_borrows": total_borrows,
            "active_borrows": active_borrows,
            "overdue_borrows": overdue_borrows
        })
        student_responses.append(student_dict)
    
    return student_responses

# Borrow management endpoints
@app.post("/api/borrows/", response_model=schemas.BorrowResponse)
async def create_borrow(
    borrow: schemas.BorrowCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if book exists and is available
    book = db.query(models.Book).filter(models.Book.id == borrow.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.available_quantity <= 0:
        raise HTTPException(status_code=400, detail="No copies available for borrowing")

    # Check if student exists and is active
    student = db.query(models.Student).filter(models.Student.id == borrow.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if not student.is_active:
        raise HTTPException(status_code=400, detail="Student is not active")

    # Check if student has reached their limit
    active_borrows = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.student_id == student.id,
        models.BorrowRecord.return_date == None
    ).count()
    
    if active_borrows >= 3:  # Maximum 3 books per student
        raise HTTPException(
            status_code=400,
            detail="Student has reached maximum borrow limit (3 books)"
        )

    # Create borrow record
    db_borrow = models.BorrowRecord(
        book_id=book.id,
        student_id=student.id,
        admin_id=current_admin.id,
        borrow_date=datetime.utcnow(),
        due_date=borrow.due_date,
    
    )
    
    # Update available quantity
    book.available_quantity -= 1
    
    db.add(db_borrow)
    db.commit()
    db.refresh(db_borrow)
    return db_borrow

@app.post("/api/borrows/{borrow_id}/return", response_model=schemas.BorrowResponse)
async def return_book(
    borrow_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get borrow record with book relationship
    borrow = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.id == borrow_id
    ).options(
        joinedload(models.BorrowRecord.book)
    ).first()
    
    if not borrow:
        raise HTTPException(status_code=404, detail="Borrow record not found")

    if borrow.return_date:
        raise HTTPException(status_code=400, detail="Book already returned")

    # Update borrow record
    borrow.return_date = datetime.utcnow()
    
    # Increase available quantity
    book = borrow.book
    book.available_quantity += 1
    
    db.commit()
    db.refresh(borrow)
    return borrow

@app.get("/api/borrows/", response_model=List[schemas.BorrowResponse])
async def list_borrows(
    skip: int = 0,
    limit: int = 10,
    student_id: Optional[int] = None,
    book_id: Optional[int] = None,
    status: Optional[str] = None,  # active, returned, overdue
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Base query
    query = db.query(models.BorrowRecord)
    
    # Apply filters
    if student_id:
        query = query.filter(models.BorrowRecord.student_id == student_id)
    if book_id:
        query = query.filter(models.BorrowRecord.book_id == book_id)
    if status:
        if status == "active":
            query = query.filter(models.BorrowRecord.return_date == None)
        elif status == "returned":
            query = query.filter(models.BorrowRecord.return_date != None)
        elif status == "overdue":
            query = query.filter(
                models.BorrowRecord.return_date == None,
                models.BorrowRecord.due_date < datetime.utcnow()
            )
    
    return query.offset(skip).limit(limit).all()

@app.get("/api/borrows/{borrow_id}", response_model=schemas.BorrowResponse)
async def get_borrow(
    borrow_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_borrow = db.query(models.BorrowRecord).filter(models.BorrowRecord.id == borrow_id).first()
    if not db_borrow:
        raise HTTPException(status_code=404, detail="Borrow record not found")

    return db_borrow

# Reports endpoints
@app.get("/api/reports/", response_model=schemas.ReportResponse)
async def get_reports(
    date_range: schemas.DateRangeFilter = Depends(),
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Base query for date range
    query = db.query(models.BorrowRecord)
    if date_range.start_date:
        query = query.filter(models.BorrowRecord.borrow_date >= date_range.start_date)
    if date_range.end_date:
        query = query.filter(models.BorrowRecord.borrow_date <= date_range.end_date)
    
    # Get borrow statistics
    total_borrows = query.count()
    active_borrows = query.filter(models.BorrowRecord.return_date == None).count()
    overdue_borrows = query.filter(
        models.BorrowRecord.return_date == None,
        models.BorrowRecord.due_date < datetime.utcnow()
    ).count()
    returned_borrows = query.filter(models.BorrowRecord.return_date != None).count()
    
    # Get books by category
    books_by_category = {}
    for category in BookCategory:
        count = query.join(models.Book).filter(models.Book.category == category).count()
        if count > 0:
            books_by_category[category] = count
    
    # Get borrows by department
    borrows_by_department = {}
    for department in Department:
        count = query.join(models.Student).filter(models.Student.department == department).count()
        if count > 0:
            borrows_by_department[department] = count
    
    # Get popular books
    popular_books_query = db.query(
        models.Book,
        func.count(models.BorrowRecord.id).label('borrow_count')
    ).join(models.BorrowRecord).group_by(models.Book.id).order_by(desc('borrow_count')).limit(5)
    
    popular_books = []
    for book, count in popular_books_query.all():
        popular_books.append({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "category": book.category,
            "borrow_count": count
        })
    
    # Get recent borrows
    recent_borrows = query.order_by(desc(models.BorrowRecord.borrow_date)).limit(5).all()
    
    return {
        "stats": {
            "total_borrows": total_borrows,
            "active_borrows": active_borrows,
            "overdue_borrows": overdue_borrows,
            "returned_borrows": returned_borrows,
            "books_by_category": books_by_category,
            "borrows_by_department": borrows_by_department
        },
        "popular_books": popular_books,
        "recent_borrows": recent_borrows
    }


# Middleware to handle authentication redirects
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not request.url.path.startswith("/login"):
        token = request.cookies.get("access_token")
        if not token or not token.startswith("Bearer "):
            return RedirectResponse(url="/login", status_code=303)
        try:
            token_data = verify_token(token.split(" ")[1])
            if not token_data:
                return RedirectResponse(url="/login", status_code=303)
        except:
            return RedirectResponse(url="/login", status_code=303)
    response = await call_next(request)
    return response

# Helper functions for enums
def get_categories():
    return [{"value": category.value} for category in BookCategory]

def get_departments():
    return [{"value": dept.value} for dept in Department]

# Setup templates and static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Add session middleware with a secret key
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-here")

# Frontend routes
@app.get("/books")
async def books_page(
    request: Request,
    page: int = 1,
    search: str = None,
    category: str = None,
    availability: str = None,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(database.get_db)
):
    if not current_admin:
        return RedirectResponse(url="/login", status_code=303)
        
    # Query books with filters
    query = db.query(models.Book)
    if search:
        query = query.filter(
            or_(
                models.Book.title.ilike(f"%{search}%"),
                models.Book.author.ilike(f"%{search}%"),
                models.Book.isbn.ilike(f"%{search}%")
            )
        )
    if category:
        query = query.filter(models.Book.category == category)
    if availability:
        if availability == "available":
            query = query.filter(models.Book.available_quantity > 0)
        elif availability == "borrowed":
            query = query.filter(models.Book.available_quantity == 0)
            
    # Pagination
    total = query.count()
    per_page = 10
    total_pages = (total + per_page - 1) // per_page
    
    books = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return templates.TemplateResponse(
        "books.html",
        {
            "request": request,
            "books": books,
            "current_admin": current_admin,
            "categories": get_categories(),
            "current_page": page,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
            "active_page": "books"
        }
    )

@app.get("/students")
async def students_page(
    request: Request,
    page: int = 1,
    search: str = None,
    department: str = None,
    status: str = None,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(database.get_db)
):
    if not current_admin:
        return RedirectResponse(url="/login", status_code=303)
        
    # Query students with filters
    query = db.query(models.Student)
    if search:
        query = query.filter(
            or_(
                models.Student.student_id.ilike(f"%{search}%"),
                models.Student.fullname.ilike(f"%{search}%"),
                models.Student.email.ilike(f"%{search}%")
            )
        )
    if department:
        query = query.filter(models.Student.department == department)
    if status:
        if status == "active":
            query = query.filter(models.Student.is_active == True)
        elif status == "inactive":
            query = query.filter(models.Student.is_active == False)
            
    # Pagination
    total = query.count()
    per_page = 10
    total_pages = (total + per_page - 1) // per_page
    
    students = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return templates.TemplateResponse(
        "students.html",
        {
            "request": request,
            "students": students,
            "current_admin": current_admin,
            "departments": get_departments(),
            "current_page": page,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
            "active_page": "students"
        }
    )

@app.get("/borrows")
async def borrows_page(
    request: Request,
    page: int = 1,
    search: str = None,
    status: str = None,
    start_date: str = None,
    end_date: str = None,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(database.get_db)
):
    if not current_admin:
        return RedirectResponse(url="/login", status_code=303)
        
    # Query borrows with filters
    query = db.query(models.BorrowRecord)
    if search:
        query = query.join(models.Book).join(models.Student).filter(
            or_(
                models.Book.title.ilike(f"%{search}%"),
                models.Student.fullname.ilike(f"%{search}%"),
                models.Student.student_id.ilike(f"%{search}%")
            )
        )
    if status:
        if status == "borrowed":
            query = query.filter(models.BorrowRecord.return_date == None)
        elif status == "returned":
            query = query.filter(models.BorrowRecord.return_date != None)
        elif status == "overdue":
            query = query.filter(
                and_(
                    models.BorrowRecord.return_date == None,
                    models.BorrowRecord.due_date < datetime.now()
                )
            )
    if start_date:
        query = query.filter(models.BorrowRecord.borrow_date >= start_date)
    if end_date:
        query = query.filter(models.BorrowRecord.borrow_date <= end_date)
            
    # Pagination
    total = query.count()
    per_page = 10
    total_pages = (total + per_page - 1) // per_page
    
    borrows = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Get available books for new borrow
    available_books = db.query(models.Book).filter(models.Book.available_quantity > 0).all()
    
    return templates.TemplateResponse(
        "borrows.html",
        {
            "request": request,
            "borrows": borrows,
            "current_admin": current_admin,
            "available_books": available_books,
            "students": db.query(models.Student).filter(models.Student.is_active == True).all(),
            "current_page": page,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
            "active_page": "borrows"
        }
    )

@app.get("/reports")
async def reports_page(
    request: Request,
    report_type: str = "borrows",
    start_date: str = None,
    end_date: str = None,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(database.get_db)
):
    if not current_admin:
        return RedirectResponse(url="/login", status_code=303)
        
    # Get statistics
    stats = {
        "total_borrows": db.query(models.BorrowRecord).count(),
        "active_borrows": db.query(models.BorrowRecord).filter(models.BorrowRecord.return_date == None).count(),
        "overdue_books": db.query(models.BorrowRecord).filter(
            and_(
                models.BorrowRecord.return_date == None,
                models.BorrowRecord.due_date < datetime.now()
            )
        ).count(),
        "active_students": db.query(models.Student).filter(models.Student.is_active == True).count()
    }
    
    # Get borrow trends (last 7 days)
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    trends_query = db.query(
        func.date(models.BorrowRecord.borrow_date).label('date'),
        func.count().label('count')
    ).filter(
        func.date(models.BorrowRecord.borrow_date) >= week_ago
    ).group_by(
        func.date(models.BorrowRecord.borrow_date)
    ).order_by(
        func.date(models.BorrowRecord.borrow_date)
    )
    
    borrow_trends = {
        "labels": [],
        "data": []
    }
    for trend in trends_query.all():
        borrow_trends["labels"].append(datetime.strptime(trend.date, "%Y-%m-%d").strftime("%Y-%m-%d"))
        borrow_trends["data"].append(trend.count)
        
    # Get popular books
    popular_books_query = db.query(
        models.Book.title,
        func.count().label('borrow_count')
    ).join(
        models.BorrowRecord
    ).group_by(
        models.Book.title
    ).order_by(
        func.count().desc()
    ).limit(5)
    
    popular_books = {
        "labels": [],
        "data": []
    }
    for book in popular_books_query.all():
        popular_books["labels"].append(book.title)
        popular_books["data"].append(book.borrow_count)
    
    # Get recent borrows
    recent_borrows = trends_query.order_by(desc(models.BorrowRecord.borrow_date)).limit(5).all()
    
    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "current_admin": current_admin,
            "stats": stats,
            "borrow_trends": borrow_trends,
            "popular_books": popular_books,
            "recent_borrows": recent_borrows
        }
    )

@app.get("/reports/export")
async def export_report(
    report_type: str = "borrows",
    start_date: str = None,
    end_date: str = None,
    current_admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(database.get_db)
):
    if not current_admin:
        return RedirectResponse(url="/login", status_code=303)
        
    # Implementation for report export
    pass

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_admin: Optional[models.Admin] = Depends(get_current_admin)):
    if current_admin:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_admin: Optional[models.Admin] = Depends(get_current_admin)
):
    if current_admin:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    admin = authenticate_admin(db, form_data.username, form_data.password)
    if not admin:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid username or password"
            },
            status_code=401
        )

    access_token = create_access_token(data={"sub": admin.username})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,  # 30 minutes
        samesite="lax"
    )
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response

@app.get("/books/", response_class=HTMLResponse)
async def books_page(
    request: Request,
    current_admin: Optional[models.Admin] = Depends(get_current_admin),
    db: Session = Depends(database.get_db)
):
    if not current_admin:
        return RedirectResponse(url="/login")
    
    books = db.query(models.Book).all()
    categories = [category.value for category in BookCategory]
    departments = [dept.value for dept in Department]
    
    return templates.TemplateResponse(
        "books.html",
        {
            "request": request,
            "current_admin": current_admin,
            "books": books,
            "categories": categories,
            "departments": departments
        }
    )

def get_current_time():
    """Get current time in UTC with timezone info"""
    return datetime.now(timezone.utc)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        return RedirectResponse(url="/login")

    # Get current time in UTC
    current_time = get_current_time()

    # Get statistics
    stats = {
        "total_books": db.query(models.Book).count(),
        "active_students": db.query(models.Student).filter(models.Student.is_active == True).count(),
        "borrowed_books": db.query(models.BorrowRecord).filter(
            models.BorrowRecord.return_date == None
        ).count(),
        "overdue_books": db.query(models.BorrowRecord).filter(
            models.BorrowRecord.return_date == None,
            models.BorrowRecord.due_date < current_time
        ).count()
    }

    # Get recent borrows
    recent_borrows = db.query(models.BorrowRecord).order_by(
        desc(models.BorrowRecord.borrow_date)
    ).limit(5).all()

    # Make datetime objects timezone-aware
    for borrow in recent_borrows:
        if borrow.borrow_date and borrow.borrow_date.tzinfo is None:
            borrow.borrow_date = borrow.borrow_date.replace(tzinfo=timezone.utc)
        if borrow.due_date and borrow.due_date.tzinfo is None:
            borrow.due_date = borrow.due_date.replace(tzinfo=timezone.utc)
        if borrow.return_date and borrow.return_date.tzinfo is None:
            borrow.return_date = borrow.return_date.replace(tzinfo=timezone.utc)

    # Format recent activities
    recent_activities = [
        {
            "timestamp": borrow.borrow_date.strftime("%Y-%m-%d %H:%M"),
            "description": (
                f"{'Returned' if borrow.return_date else 'Borrowed'}: "
                f"{borrow.book.title} by {borrow.student.fullname}"
            )
        }
        for borrow in recent_borrows
    ]

    # Get department distribution
    department_stats = {}
    for dept in Department:
        count = db.query(models.Student).filter(
            models.Student.department == dept,
            models.Student.is_active == True
        ).count()
        if count > 0:
            department_stats[dept.value] = count

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_admin": current_admin,
            "active_page": "dashboard",
            "stats": stats,
            "recent_borrows": recent_borrows,
            "recent_activities": recent_activities,
            "department_labels": list(department_stats.keys()),
            "department_data": list(department_stats.values()),
            "now": current_time
        }
    )

@app.get("/reports/data")
async def get_report_data(
    request: Request,
    report_type: str = "all",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Convert string dates to datetime if provided
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    # Base query
    base_query = db.query(models.BorrowRecord)
    if start_datetime:
        base_query = base_query.filter(models.BorrowRecord.borrow_date >= start_datetime)
    if end_datetime:
        base_query = base_query.filter(models.BorrowRecord.borrow_date <= end_datetime)

    # Get basic statistics
    stats = {
        "total_borrows": base_query.count(),
        "active_borrows": base_query.filter(models.BorrowRecord.return_date == None).count(),
        "overdue_borrows": base_query.filter(
            models.BorrowRecord.return_date == None,
            models.BorrowRecord.due_date < datetime.utcnow()
        ).count()
    }

    # Get borrow trends
    trends_query = db.query(
        func.date(models.BorrowRecord.borrow_date).label('date'),
        func.count(models.BorrowRecord.id).label('count')
    )
    if start_datetime:
        trends_query = trends_query.filter(models.BorrowRecord.borrow_date >= start_datetime)
    if end_datetime:
        trends_query = trends_query.filter(models.BorrowRecord.borrow_date <= end_datetime)
    
    trends = trends_query.group_by(
        func.date(models.BorrowRecord.borrow_date)
    ).order_by(
        func.date(models.BorrowRecord.borrow_date)
    ).all()

    borrow_trends = {
        "labels": [],
        "data": []
    }

    if trends:
        # Fill in missing dates with zero counts
        current_date = trends[0][0]  # First date in results
        end_date = trends[-1][0]  # Last date in results
        trend_dict = {trend[0]: trend[1] for trend in trends}

        while current_date <= end_date:
            borrow_trends["labels"].append(current_date.strftime("%Y-%m-%d"))
            borrow_trends["data"].append(trend_dict.get(current_date, 0))
            current_date += timedelta(days=1)

    # Get popular books
    popular_books = {
        "labels": [],
        "data": []
    }

    popular_books_query = db.query(
        models.Book,
        func.count(models.BorrowRecord.id).label('borrow_count')
    ).join(models.BorrowRecord)
    
    if start_datetime:
        popular_books_query = popular_books_query.filter(models.BorrowRecord.borrow_date >= start_datetime)
    if end_datetime:
        popular_books_query = popular_books_query.filter(models.BorrowRecord.borrow_date <= end_datetime)
    
    popular_books_results = popular_books_query.group_by(
        models.Book.id
    ).order_by(
        desc('borrow_count')
    ).limit(5).all()

    for book, count in popular_books_results:
        popular_books["labels"].append(book.title)
        popular_books["data"].append(count)

    # Get recent borrows
    recent_borrows = base_query.order_by(
        desc(models.BorrowRecord.borrow_date)
    ).limit(5).all()

    return {
        "stats": stats,
        "borrow_trends": borrow_trends,
        "popular_books": popular_books,
        "recent_borrows": [
            {
                "id": borrow.id,
                "book_title": borrow.book.title,
                "student_name": borrow.student.fullname,
                "borrow_date": borrow.borrow_date.strftime("%Y-%m-%d"),
                "due_date": borrow.due_date.strftime("%Y-%m-%d"),
                "return_date": borrow.return_date.strftime("%Y-%m-%d") if borrow.return_date else None,
                "is_overdue": borrow.is_overdue
            }
            for borrow in recent_borrows
        ]
    }

# Book CRUD Operations
@app.put("/api/books/{book_id}", response_model=schemas.BookResponse)
async def update_book(
    book_id: int,
    book_update: schemas.BookUpdate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if ISBN is being updated and is unique
    if book_update.isbn and book_update.isbn != db_book.isbn:
        existing_book = db.query(models.Book).filter(
            models.Book.isbn == book_update.isbn
        ).first()
        if existing_book:
            raise HTTPException(
                status_code=400,
                detail="ISBN already registered"
            )

    # Handle quantity update
    if book_update.quantity is not None:
        if book_update.quantity < (db_book.quantity - db_book.available_quantity):
            raise HTTPException(
                status_code=400,
                detail="Cannot reduce quantity below number of borrowed books"
            )
        borrowed_count = db_book.quantity - db_book.available_quantity
        db_book.available_quantity = book_update.quantity - borrowed_count
        db_book.quantity = book_update.quantity

    # Update other book fields
    update_data = book_update.model_dump(exclude_unset=True)
    if 'quantity' in update_data:
        del update_data['quantity']  # Already handled above
    
    for field, value in update_data.items():
        setattr(db_book, field, value)

    db.commit()
    db.refresh(db_book)
    return db_book

@app.delete("/api/books/{book_id}")
async def delete_book(
    book_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if book has active borrows
    active_borrow = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.book_id == book_id,
        models.BorrowRecord.return_date == None
    ).first()

    if active_borrow:
        raise HTTPException(status_code=400, detail="Cannot delete book with active borrows")
        
    # Delete book
    db.delete(db_book)
    db.commit()
    return {"message": "Book deleted successfully"}

@app.post("/api/borrows/", response_model=schemas.BorrowResponse)
async def create_borrow(
    borrow: schemas.BorrowCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get book and student
    book = db.query(models.Book).filter(models.Book.id == borrow.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    student = db.query(models.Student).filter(models.Student.id == borrow.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Check if book is available
    if book.available_quantity <= 0:
        raise HTTPException(status_code=400, detail="No copies available for borrowing")
    
    # Check if student has reached their limit
    active_borrows = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.student_id == student.id,
        models.BorrowRecord.return_date == None
    ).count()
    if active_borrows >= 3:  # Maximum 3 books per student
        raise HTTPException(
            status_code=400,
            detail="Student has reached maximum borrow limit (3 books)"
        )
    
    # Check if student has overdue books
    if student.has_overdue_books:
        raise HTTPException(
            status_code=400,
            detail="Student has overdue books and cannot borrow more books"
        )
    
    # Create borrow record
    db_borrow = models.BorrowRecord(
        book_id=book.id,
        student_id=student.id,
        admin_id=current_admin.id,
        due_date=borrow.due_date
    )
    
    # Update book status
    book.available_quantity -= 1

    db.add(db_borrow)
    db.commit()
    db.refresh(db_borrow)
    
    return db_borrow

@app.post("/api/borrows/{borrow_id}/return", response_model=schemas.BorrowResponse)
async def return_book(
    borrow_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get borrow record
    borrow = db.query(models.BorrowRecord).filter(models.BorrowRecord.id == borrow_id).first()
    if not borrow:
        raise HTTPException(status_code=404, detail="Borrow record not found")
    
    # Check if book is already returned
    if borrow.return_date:
        raise HTTPException(status_code=400, detail="Book already returned")
    
    # Update borrow record and book status
    borrow.return_date = datetime.utcnow()
    borrow.book.available_quantity += 1
    
    db.commit()
    db.refresh(borrow)
    
    return borrow

@app.get("/api/borrows/", response_model=List[schemas.BorrowResponse])
async def list_borrows(
    skip: int = 0,
    limit: int = 10,
    student_id: Optional[int] = None,
    book_id: Optional[int] = None,
    status: Optional[str] = None,  # active, returned, overdue
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Base query
    query = db.query(models.BorrowRecord)
    
    # Apply filters
    if student_id:
        query = query.filter(models.BorrowRecord.student_id == student_id)
    if book_id:
        query = query.filter(models.BorrowRecord.book_id == book_id)
    if status:
        if status == "active":
            query = query.filter(models.BorrowRecord.return_date == None)
        elif status == "returned":
            query = query.filter(models.BorrowRecord.return_date != None)
        elif status == "overdue":
            query = query.filter(
                models.BorrowRecord.return_date == None,
                models.BorrowRecord.due_date < datetime.utcnow()
            )
    
    return query.offset(skip).limit(limit).all()

@app.get("/api/borrows/{borrow_id}", response_model=schemas.BorrowResponse)
async def get_borrow(
    borrow_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_borrow = db.query(models.BorrowRecord).filter(models.BorrowRecord.id == borrow_id).first()
    if not db_borrow:
        raise HTTPException(status_code=404, detail="Borrow record not found")

    return db_borrow

# Student CRUD Operations
@app.put("/api/students/{student_id}", response_model=schemas.Student)
async def update_student(
    student_id: int,
    student_update: schemas.StudentUpdate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check if email is being updated and is unique
    if student_update.email and student_update.email != db_student.email:
        existing_student = db.query(models.Student).filter(
            models.Student.email == student_update.email
        ).first()
        if existing_student:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

    # Update student fields
    update_data = student_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_student, field, value)
        
    db.commit()
    db.refresh(db_student)
    return db_student

@app.delete("/api/students/{student_id}")
async def delete_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check if student has any active borrows
    active_borrow = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.student_id == student_id,
        models.BorrowRecord.return_date == None
    ).first()

    if active_borrow:
        raise HTTPException(status_code=400, detail="Cannot delete student with active borrows")
        
    # Delete student
    db.delete(db_student)
    db.commit()
    return {"message": "Student deleted successfully"}

# Borrow CRUD Operations
@app.put("/api/borrows/{borrow_id}", response_model=schemas.BorrowResponse)
async def update_borrow(
    borrow_id: int,
    borrow_update: schemas.BorrowUpdate,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_borrow = db.query(models.BorrowRecord).filter(models.BorrowRecord.id == borrow_id).first()
    if not db_borrow:
        raise HTTPException(status_code=404, detail="Borrow record not found")

    # Only allow updating certain fields
    for field, value in borrow_update.dict(exclude_unset=True).items():
        if field in ['due_date', 'notes']:
            setattr(db_borrow, field, value)

    db.commit()
    db.refresh(db_borrow)
    return db_borrow

@app.delete("/api/borrows/{borrow_id}")
async def delete_borrow(
    borrow_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.Admin = Depends(get_current_admin)
):
    if not current_admin:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_borrow = db.query(models.BorrowRecord).filter(models.BorrowRecord.id == borrow_id).first()
    if not db_borrow:
        raise HTTPException(status_code=404, detail="Borrow record not found")

    # Only allow deleting returned borrows
    if not db_borrow.return_date:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete active borrow record"
        )

    db.delete(db_borrow)
    db.commit()
    return {"success": True}
