# Library Management System

A modern web-based library management system built with FastAPI, SQLAlchemy, and Bootstrap. This system helps librarians efficiently manage books, students, and borrowing records.

## Features

### 1. Book Management
- Add, edit, and delete books
- Track book availability and total copies
- Categorize books by subject
- Search books by title, author, or ISBN
- Filter books by category and availability status

### 2. Student Management
- Register and manage student accounts
- Track student borrowing history
- Monitor active and overdue books
- Set borrowing limits per student
- Filter students by department and status

### 3. Borrowing System
- Issue books to students
- Track due dates and return dates
- Handle book returns
- Generate overdue notifications
- View borrowing history

### 4. Reports and Analytics
- Generate borrowing statistics
- View popular books
- Track department-wise borrowing patterns
- Monitor overdue books
- Generate periodic reports

### 5. Search and Filter
- Advanced search functionality across books and students
- Multiple filter options
- Real-time search results
- Pagination for large result sets

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML, CSS, JavaScript
- **UI Framework**: Bootstrap 5
- **Authentication**: JWT-based authentication

## Setup and Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd library-management-system
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the database:
```bash
python init_db.py
```

5. Start the server:
```bash
python run.py
```

6. Access the application:
Open your browser and navigate to `http://localhost:8000`

## Project Structure

```
server/
├── static/          # Static files (CSS, JS, images)
├── templates/       # HTML templates
├── main.py         # Main application file
├── models.py       # Database models
├── schemas.py      # Pydantic schemas
├── database.py     # Database configuration
└── requirements.txt # Project dependencies
```

## API Documentation

The API documentation is available at `/docs` when running the server. It provides detailed information about all available endpoints and their usage.

## Authentication

The system uses JWT-based authentication. Administrators need to log in to access the system. The default admin credentials are:

- Username: admin@library.com
- Password: admin123

(Remember to change these credentials in production)

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to your branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the development team.
