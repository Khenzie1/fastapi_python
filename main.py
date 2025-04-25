# Book Publishing API

from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlite3
import os
from datetime import date

# Initialize FastAPI app
app = FastAPI(
    title="Book Publishing API",
    description="API for managing books, authors, and publishers in a publishing business",
    version="1.0.0"
)

# Database setup
DB_FILE = "publishing.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Create authors table
        cursor.execute('''
        CREATE TABLE authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            bio TEXT,
            date_registered DATE DEFAULT CURRENT_DATE
        )
        ''')
        
        # Create publishers table
        cursor.execute('''
        CREATE TABLE publishers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            email TEXT UNIQUE
        )
        ''')
        
        # Create books table
        cursor.execute('''
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            isbn TEXT UNIQUE,
            publication_date DATE,
            price REAL,
            genre TEXT,
            author_id INTEGER,
            publisher_id INTEGER,
            FOREIGN KEY (author_id) REFERENCES authors (id),
            FOREIGN KEY (publisher_id) REFERENCES publishers (id)
        )
        ''')
        
        # Insert sample data
        cursor.execute("INSERT INTO authors (name, email, bio) VALUES (?, ?, ?)", 
                      ("Jane Austen", "jane@example.com", "Famous English novelist known for her six major novels"))
        cursor.execute("INSERT INTO authors (name, email, bio) VALUES (?, ?, ?)", 
                      ("George Orwell", "george@example.com", "English novelist and essayist"))
        
        cursor.execute("INSERT INTO publishers (name, address, phone, email) VALUES (?, ?, ?, ?)", 
                      ("Penguin Random House", "123 Publishing St, NY", "555-1234", "info@prh.com"))
        cursor.execute("INSERT INTO publishers (name, address, phone, email) VALUES (?, ?, ?, ?)", 
                      ("HarperCollins", "456 Book Ave, CA", "555-5678", "info@harpercollins.com"))
        
        cursor.execute("INSERT INTO books (title, description, isbn, publication_date, price, genre, author_id, publisher_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                      ("Pride and Prejudice", "A romantic novel of manners", "9780141439518", "1813-01-28", 12.99, "Classic", 1, 1))
        cursor.execute("INSERT INTO books (title, description, isbn, publication_date, price, genre, author_id, publisher_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                      ("1984", "A dystopian social science fiction novel", "9780451524935", "1949-06-08", 14.99, "Dystopian", 2, 2))
        
        conn.commit()
        conn.close()
        print("Database initialized with sample data")

# Models
class AuthorBase(BaseModel):
    name: str
    email: Optional[str] = None
    bio: Optional[str] = None

class AuthorCreate(AuthorBase):
    pass

class Author(AuthorBase):
    id: int
    date_registered: Optional[date] = None
    
    class Config:
        orm_mode = True

class PublisherBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class PublisherCreate(PublisherBase):
    pass

class Publisher(PublisherBase):
    id: int
    
    class Config:
        orm_mode = True

class BookBase(BaseModel):
    title: str
    description: Optional[str] = None
    isbn: Optional[str] = None
    publication_date: Optional[date] = None
    price: Optional[float] = Field(None, ge=0)
    genre: Optional[str] = None
    author_id: Optional[int] = None
    publisher_id: Optional[int] = None

class BookCreate(BookBase):
    pass

class Book(BookBase):
    id: int
    
    class Config:
        orm_mode = True

# Initialize DB at startup
@app.on_event("startup")
def startup_event():
    init_db()

# Author endpoints
@app.post("/authors/", response_model=Author, tags=["Authors"])
def create_author(author: AuthorCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Create a new author with the following information:
    
    - *name*: Required name of the author
    - *email*: Optional email address
    - *bio*: Optional author biography
    """
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO authors (name, email, bio) VALUES (?, ?, ?)",
        (author.name, author.email, author.bio)
    )
    db.commit()
    author_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM authors WHERE id = ?", (author_id,))
    result = cursor.fetchone()
    return dict(result)

@app.get("/authors/", response_model=List[Author], tags=["Authors"])
def read_authors(skip: int = 0, limit: int = 100, db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieve a list of authors with pagination:
    
    - *skip*: Number of authors to skip (default: 0)
    - *limit*: Maximum number of authors to return (default: 100)
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM authors LIMIT ? OFFSET ?", (limit, skip))
    results = cursor.fetchall()
    return [dict(result) for result in results]

@app.get("/authors/{author_id}", response_model=Author, tags=["Authors"])
def read_author(author_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieve an author by their ID:
    
    - *author_id*: The ID of the author to retrieve
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM authors WHERE id = ?", (author_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Author not found")
    return dict(result)

@app.put("/authors/{author_id}", response_model=Author, tags=["Authors"])
def update_author(author_id: int, author: AuthorCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Update an author's information:
    
    - *author_id*: The ID of the author to update
    - *author*: The updated author information
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM authors WHERE id = ?", (author_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Author not found")
    
    cursor.execute(
        "UPDATE authors SET name = ?, email = ?, bio = ? WHERE id = ?",
        (author.name, author.email, author.bio, author_id)
    )
    db.commit()
    
    cursor.execute("SELECT * FROM authors WHERE id = ?", (author_id,))
    result = cursor.fetchone()
    return dict(result)

@app.delete("/authors/{author_id}", tags=["Authors"])
def delete_author(author_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Delete an author:
    
    - *author_id*: The ID of the author to delete
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM authors WHERE id = ?", (author_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Author not found")
    
    cursor.execute("DELETE FROM authors WHERE id = ?", (author_id,))
    db.commit()
    return {"message": f"Author {author_id} deleted successfully"}

# Publisher endpoints
@app.post("/publishers/", response_model=Publisher, tags=["Publishers"])
def create_publisher(publisher: PublisherCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Create a new publisher with the following information:
    
    - *name*: Required name of the publisher
    - *address*: Optional physical address
    - *phone*: Optional phone number
    - *email*: Optional email address
    """
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO publishers (name, address, phone, email) VALUES (?, ?, ?, ?)",
        (publisher.name, publisher.address, publisher.phone, publisher.email)
    )
    db.commit()
    publisher_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM publishers WHERE id = ?", (publisher_id,))
    result = cursor.fetchone()
    return dict(result)

@app.get("/publishers/", response_model=List[Publisher], tags=["Publishers"])
def read_publishers(skip: int = 0, limit: int = 100, db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieve a list of publishers with pagination:
    
    - *skip*: Number of publishers to skip (default: 0)
    - *limit*: Maximum number of publishers to return (default: 100)
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM publishers LIMIT ? OFFSET ?", (limit, skip))
    results = cursor.fetchall()
    return [dict(result) for result in results]

@app.get("/publishers/{publisher_id}", response_model=Publisher, tags=["Publishers"])
def read_publisher(publisher_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieve a publisher by their ID:
    
    - *publisher_id*: The ID of the publisher to retrieve
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM publishers WHERE id = ?", (publisher_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Publisher not found")
    return dict(result)

@app.put("/publishers/{publisher_id}", response_model=Publisher, tags=["Publishers"])
def update_publisher(publisher_id: int, publisher: PublisherCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Update a publisher's information:
    
    - *publisher_id*: The ID of the publisher to update
    - *publisher*: The updated publisher information
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM publishers WHERE id = ?", (publisher_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Publisher not found")
    
    cursor.execute(
        "UPDATE publishers SET name = ?, address = ?, phone = ?, email = ? WHERE id = ?",
        (publisher.name, publisher.address, publisher.phone, publisher.email, publisher_id)
    )
    db.commit()
    
    cursor.execute("SELECT * FROM publishers WHERE id = ?", (publisher_id,))
    result = cursor.fetchone()
    return dict(result)

@app.delete("/publishers/{publisher_id}", tags=["Publishers"])
def delete_publisher(publisher_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Delete a publisher:
    
    - *publisher_id*: The ID of the publisher to delete
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM publishers WHERE id = ?", (publisher_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Publisher not found")
    
    cursor.execute("DELETE FROM publishers WHERE id = ?", (publisher_id,))
    db.commit()
    return {"message": f"Publisher {publisher_id} deleted successfully"}

# Book endpoints
@app.post("/books/", response_model=Book, tags=["Books"])
def create_book(book: BookCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Create a new book with the following information:
    
    - *title*: Required title of the book
    - *description*: Optional book description
    - *isbn*: Optional ISBN identifier
    - *publication_date*: Optional date of publication
    - *price*: Optional price (must be non-negative)
    - *genre*: Optional book genre
    - *author_id*: Optional ID of the author
    - *publisher_id*: Optional ID of the publisher
    """
    cursor = db.cursor()
    
    # Validate author_id if provided
    if book.author_id is not None:
        cursor.execute("SELECT id FROM authors WHERE id = ?", (book.author_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Author not found")
    
    # Validate publisher_id if provided
    if book.publisher_id is not None:
        cursor.execute("SELECT id FROM publishers WHERE id = ?", (book.publisher_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Publisher not found")
    
    cursor.execute(
        "INSERT INTO books (title, description, isbn, publication_date, price, genre, author_id, publisher_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (book.title, book.description, book.isbn, book.publication_date, book.price, book.genre, book.author_id, book.publisher_id)
    )
    db.commit()
    book_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    result = cursor.fetchone()
    return dict(result)

@app.get("/books/", response_model=List[Book], tags=["Books"])
def read_books(
    skip: int = 0, 
    limit: int = 100, 
    genre: Optional[str] = Query(None, description="Filter books by genre"),
    author_id: Optional[int] = Query(None, description="Filter books by author ID"),
    publisher_id: Optional[int] = Query(None, description="Filter books by publisher ID"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Retrieve a list of books with filtering and pagination:
    
    - *skip*: Number of books to skip (default: 0)
    - *limit*: Maximum number of books to return (default: 100)
    - *genre*: Optional genre filter
    - *author_id*: Optional filter by author ID
    - *publisher_id*: Optional filter by publisher ID
    """
    cursor = db.cursor()
    
    query = "SELECT * FROM books"
    params = []
    
    # Build WHERE clause based on filters
    conditions = []
    if genre:
        conditions.append("genre = ?")
        params.append(genre)
    if author_id:
        conditions.append("author_id = ?")
        params.append(author_id)
    if publisher_id:
        conditions.append("publisher_id = ?")
        params.append(publisher_id)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    # Add pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, skip])
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    return [dict(result) for result in results]

@app.get("/books/{book_id}", response_model=Book, tags=["Books"])
def read_book(book_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieve a book by its ID:
    
    - *book_id*: The ID of the book to retrieve
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return dict(result)

@app.put("/books/{book_id}", response_model=Book, tags=["Books"])
def update_book(book_id: int, book: BookCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Update a book's information:
    
    - *book_id*: The ID of the book to update
    - *book*: The updated book information
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Validate author_id if provided
    if book.author_id is not None:
        cursor.execute("SELECT id FROM authors WHERE id = ?", (book.author_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Author not found")
    
    # Validate publisher_id if provided
    if book.publisher_id is not None:
        cursor.execute("SELECT id FROM publishers WHERE id = ?", (book.publisher_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Publisher not found")
    
    cursor.execute(
        "UPDATE books SET title = ?, description = ?, isbn = ?, publication_date = ?, price = ?, genre = ?, author_id = ?, publisher_id = ? WHERE id = ?",
        (book.title, book.description, book.isbn, book.publication_date, book.price, book.genre, book.author_id, book.publisher_id, book_id)
    )
    db.commit()
    
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    result = cursor.fetchone()
    return dict(result)

@app.delete("/books/{book_id}", tags=["Books"])
def delete_book(book_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Delete a book:
    
    - *book_id*: The ID of the book to delete
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return {"message": f"Book {book_id} deleted successfully"}

if __name__ == "_main_":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

    