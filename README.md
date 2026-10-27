# FastAPI Async Blog & REST API

A high-performance, asynchronous blog platform and production-grade REST API built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostgreSQL (psycopg 3)**, **Alembic**, and **Pydantic v2**.

This project provides both an interactive server-rendered web interface (Jinja2 + Bootstrap) and a comprehensive, fully-documented REST API with JWT authentication, Argon2 password hashing, transactional emails via `aiosmtplib`, and cloud media storage powered by **Amazon S3** and **Pillow**.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Architecture](#project-architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
  - [Database Migrations](#database-migrations)
  - [Seeding Sample Data](#seeding-sample-data)
  - [Verifying AWS S3](#verifying-aws-s3)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Key API Endpoints](#key-api-endpoints)
- [Running Tests](#running-tests)
- [Windows Async Event Loop Note](#windows-async-event-loop-note)
- [License](#license)

---

## Features

- ⚡ **100% Asynchronous Pipeline**: Built entirely around non-blocking I/O using Python's `async`/`await`, `AsyncSession`, and `psycopg` (v3).
- 🔐 **Robust Authentication & Security**:
  - Secure password hashing using **Argon2** (`pwdlib.PasswordHash.recommended()`).
  - Stateless API authentication via **JWT Access Tokens** (`PyJWT`).
  - Secure **Password Reset Flow** using cryptographically random, SHA-256 hashed database-persisted tokens with expiration.
  - Granular ownership verification on post mutation and deletion (`HTTP 403 Forbidden`).
- 📝 **Post & User Management**:
  - Full CRUD for blog posts with support for full updates (`PUT`) and partial updates (`PATCH`).
  - Flexible pagination (`skip`, `limit`, `total`, `has_more`).
  - Optimized database queries using eager loading (`selectinload`) to eliminate N+1 queries.
- 🖼️ **Cloud Media Storage (AWS S3 & Pillow)**:
  - Non-blocking image processing via `starlette.concurrency.run_in_threadpool`.
  - Automatic EXIF orientation normalization, resizing (300x300 square crop), compression, and upload to Amazon S3.
  - Automatic deletion of obsolete avatars from S3 when updated.
- 📧 **Asynchronous Transactional Email**:
  - Non-blocking email dispatch via `aiosmtplib`.
  - Responsive HTML email templates rendered with Jinja2.
- 🎨 **Dual-Layer Interface**:
  - **REST API** with automatic OpenAPI documentation.
  - **Server-Rendered UI** using Jinja2 templates and Bootstrap with dynamic client-side authentication.
- 🩺 **Health Checks & Error Handling**:
  - Automated database connectivity health checks at `/health`.
  - Unified exception handling with tailored JSON responses for API routes and custom HTML error pages for browser views.
- 🧪 **Enterprise Test Suite**:
  - Full test coverage with `pytest` and `httpx.AsyncClient`.
  - Transaction rollback per test for zero database leakage.
  - AWS S3 operations fully mocked using `moto`.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) & [Starlette](https://www.starlette.io/) |
| **Database ORM** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async Engine & Declarative Mapping) |
| **Database Driver** | [psycopg (v3)](https://www.psycopg.org/psycopg3/) with PostgreSQL |
| **Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Validation & Settings** | [Pydantic v2](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| **Auth & Security** | [PyJWT](https://pyjwt.readthedocs.io/), [pwdlib](https://frankie567.github.io/pwdlib/) (Argon2), `secrets`, `hashlib` |
| **Cloud Storage** | [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) (AWS S3) & [Pillow (PIL)](https://pillow.readthedocs.io/) |
| **Email** | [aiosmtplib](https://aiosmtplib.readthedocs.io/) |
| **Frontend / Templates** | [Jinja2](https://palletsprojects.com/p/jinja/), Bootstrap 5, Vanilla JavaScript |
| **Testing** | [pytest](https://docs.pytest.org/), [httpx](https://www.python-httpx.org/), [moto](https://docs.getmoto.org/) |

---

## Project Architecture

```
fastapi/
├── alembic/                 # Database migration scripts & environment
│   ├── versions/            # Versioned migration revisions
│   └── env.py               # Async Alembic runner with Windows event loop handling
├── routers/                 # API route controllers
│   ├── posts.py             # Post CRUD, pagination & authorization
│   └── users.py             # Auth, profile management, password reset & S3 uploads
├── static/                  # CSS stylesheets, static assets & default avatars
├── templates/               # Jinja2 HTML templates
│   ├── email/               # Transactional email templates (e.g. password_reset.html)
│   ├── account.html         # User profile & avatar update page
│   ├── home.html            # Main blog feed
│   ├── layout.html          # Base template & navigation
│   ├── login.html           # Authentication page
│   ├── post.html            # Single post view & editing
│   ├── register.html        # Account registration
│   └── user_posts.html      # Filtered posts by author
├── tests/                   # Automated test suite
│   ├── conftest.py          # Pytest fixtures, test database setup & moto S3 mock
│   ├── test_posts.py        # Post API tests
│   └── test_users.py        # User & Auth API tests
├── alembic.ini              # Alembic configuration
├── auth.py                  # JWT encoding/decoding, password hashing & dependencies
├── check_s3.py              # Utility to test AWS S3 connection and bucket permissions
├── config.py                # Pydantic BaseSettings loading from .env
├── database.py              # Async engine, sessionmaker & get_db dependency
├── email_utils.py           # Async email sending utilities via aiosmtplib
├── image_utils.py           # Pillow image processing and S3 upload/deletion helpers
├── main.py                  # Application entry point, lifespan, HTML views & error handlers
├── models.py                # SQLAlchemy ORM models (User, Post, PasswordResetToken)
├── populate_db.py           # Database seeder script with demo users and posts
├── requirements.txt         # Pinned project dependencies
└── schemas.py               # Pydantic schemas for request/response serialization
```

---

## Getting Started

### Prerequisites

- **Python 3.10+** (Python 3.13 recommended)
- **PostgreSQL 14+** running locally or in Docker
- **AWS S3 Bucket** (or compatible alternative like LocalStack/MinIO)
- **SMTP Account** (e.g., [Mailtrap](https://mailtrap.io/) for development, or SendGrid/Amazon SES for production)

---

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd fastapi
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv fastapi-venv
     .\fastapi-venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv fastapi-venv
     source fastapi-venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

### Environment Configuration

Copy the sample environment file to create your `.env`:

```bash
cp .env.example .env
```

Open `.env` and fill in your settings:

```env
# Database Configuration (PostgreSQL with psycopg v3 async driver)
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/blog_db

# Security & Authentication (JWT & Argon2)
SECRET_KEY=change_this_to_a_secure_random_string_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
RESET_TOKEN_EXPIRE_MINUTES=5

# Application Settings
FRONTEND_URL=http://localhost:8000
POST_PER_PAGE=10
MAX_UPLOAD_SIZE_BYTES=5242880

# Email Configuration (SMTP / Mailtrap)
MAIL_SERVER=smtp.mailtrap.io
MAIL_PORT=587
MAIL_USERNAME=your_smtp_username
MAIL_PASSWORD=your_smtp_password
MAIL_FROM=noreply@example.com
MAIL_USE_TLS=true

# AWS S3 Storage (Profile Pictures)
AWS_S3_BUCKET_NAME=your-s3-bucket-name
AWS_S3_REGION=us-east-1
AWS_ACCESS_KEY=your_aws_access_key
AWS_ACCESS_KEY_SECRET=your_aws_access_key_secret
# AWS_S3_ENDPOINT_URL=http://localhost:4566  # Optional: For LocalStack / MinIO
```

> [!TIP]
> You can generate a secure secret key using Python:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

---

### Database Migrations

Apply database migrations to create the required tables:

```bash
alembic upgrade head
```

To create a new migration after editing `models.py`:

```bash
alembic revision --autogenerate -m "describe changes"
alembic upgrade head
```

---

### Seeding Sample Data

Populate your database with sample authors, avatar images, and blog posts:

```bash
python populate_db.py
```

This creates 6 demo users and 44 sample posts with realistic timestamps.

---

### Verifying AWS S3

Verify that your AWS credentials and bucket permissions are working properly:

```bash
python check_s3.py
```

---

## Running the Application

Start the development server with auto-reload:

```bash
uvicorn main:app --reload
```

or using the FastAPI CLI:

```bash
fastapi dev main.py
```

The application will be accessible at:
- **Web Interface**: [http://localhost:8000](http://localhost:8000)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## API Documentation

FastAPI automatically generates interactive, OpenAPI-compliant documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Key API Endpoints

### Authentication & Users (`/api/users`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|:---:|
| `POST` | `/api/users/` | Register a new user | No |
| `POST` | `/api/users/token` | OAuth2 Password login (returns JWT) | No |
| `GET` | `/api/users/me` | Retrieve profile of the authenticated user | **Yes** |
| `PATCH`| `/api/users/me` | Update username or email | **Yes** |
| `DELETE`| `/api/users/me` | Delete current user account | **Yes** |
| `POST` | `/api/users/me/profile-picture` | Upload and resize avatar to AWS S3 | **Yes** |
| `DELETE`| `/api/users/me/profile-picture` | Remove avatar from AWS S3 (revert to default) | **Yes** |
| `POST` | `/api/users/change-password` | Update account password | **Yes** |
| `POST` | `/api/users/forgot-password` | Request password reset token via email | No |
| `POST` | `/api/users/reset-password` | Reset password using email token | No |
| `GET` | `/api/users/{user_id}` | Retrieve public profile by User ID | No |
| `GET` | `/api/users/{user_id}/posts` | List paginated posts by author ID | No |

### Blog Posts (`/api/posts`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|:---:|
| `GET` | `/api/posts/` | List all posts (supports `skip` & `limit` query parameters) | No |
| `POST` | `/api/posts/` | Create a new blog post | **Yes** |
| `GET` | `/api/posts/{post_id}` | Retrieve a specific post by ID | No |
| `PUT` | `/api/posts/{post_id}` | Full update of an existing post | **Yes (Author)** |
| `PATCH`| `/api/posts/{post_id}` | Partial update of an existing post | **Yes (Author)** |
| `DELETE`| `/api/posts/{post_id}` | Delete a post | **Yes (Author)** |

---

## Running Tests

The test suite runs against an isolated PostgreSQL test database and uses `moto` to mock AWS S3 interactions:

```bash
pytest
```

To run with verbose output:

```bash
pytest -v
```

> [!NOTE]
> Tests automatically wrap database operations in individual transaction savepoints and roll them back upon completion, leaving your test database clean.

---

## Windows Async Event Loop Note

On Windows, Python 3.8+ defaults to `ProactorEventLoop`. However, `psycopg` (v3 async engine) requires a selector event loop (`SelectorEventLoop`).

This repository already configures `asyncio.WindowsSelectorEventLoopPolicy()` in:
- [alembic/env.py](file:///D:/fastapi/alembic/env.py)
- [populate_db.py](file:///D:/fastapi/populate_db.py)
- [tests/conftest.py](file:///D:/fastapi/tests/conftest.py)

If you write standalone asynchronous scripts on Windows that connect to PostgreSQL via `psycopg`, include this block before running `asyncio.run()`:

```python
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

---

## License

This project is open-source and available under the [MIT License](LICENSE).
