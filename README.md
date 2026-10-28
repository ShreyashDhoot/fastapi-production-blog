# 🚀 FastAPI Production Blog Platform

An end-to-end, asynchronous blogging platform and REST API built with **FastAPI**, **PostgreSQL**, and **AWS S3**, featuring robust JWT authentication, comprehensive automated testing, and a hardened Linux cloud deployment.

![FastAPI Blog Platform](resource/platform-ss.png)

---

## 🌟 Key Features

### 🔐 Authentication & Security
- **Stateless JWT Tokens:** OAuth2 Bearer token authentication signed with server-side secrets and cryptographic validation.
- **Secure Password Hashing:** Modern, memory-hard **Argon2** password hashing via `pwdlib.PasswordHash.recommended()`.
- **Password Reset Flow:** Cryptographically secure, time-limited tokens generated via `secrets.token_urlsafe(32)`, SHA-256 hashed into the database, and dispatched via automated asynchronous SMTP emails.
- **Resource Authorization:** Strict ownership verification preventing unauthorized updates or deletions on posts and profile records (`HTTP 403 Forbidden`).

### 📝 Blog & Content Management
- **Full Async CRUD:** Complete asynchronous database interaction using **SQLAlchemy 2.0 (Async)** and **Psycopg 3**, featuring full updates (`PUT`) and selective partial updates (`PATCH`).
- **Cloud Media Storage:** User avatars uploaded and processed asynchronously (EXIF auto-transposition, square cropping, compression to JPEG via Pillow in a worker threadpool) and hosted on **Amazon S3**, with automatic deletion of obsolete avatars.
- **Efficient Pagination:** Server-side pagination supporting `skip`, `limit`, `total`, and `has_more` metadata, avoiding memory bloat.
- **Optimized Eager Loading:** Leverages `selectinload` to prevent N+1 query overhead and prevent asynchronous lazy-loading exceptions.

### ⚡ Architecture & UI
- **Dual-Layer Delivery:** Interactive server-rendered frontend with Jinja2 templates paired with a full-fledged, OpenAPI-compliant REST API.
- **Seamless Frontend Interactions:** Modern browser JavaScript (`fetch`) managing modal operations, dynamic authentication headers, avatar updates, and deletion workflows without full-page reloads.
- **Health Checks & Resilience:** Automated database readiness checks at `/health` and global exception handlers providing clean JSON responses for API routes and styled error templates for browsers.

---

## 🛠️ Tech Stack

| Domain | Technologies |
|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [Starlette](https://www.starlette.io/), [Pydantic v2](https://docs.pydantic.dev/) |
| **Database & ORM** | [PostgreSQL 14+](https://www.postgresql.org/), [SQLAlchemy 2.0 (Async)](https://www.sqlalchemy.org/), [psycopg 3](https://www.psycopg.org/psycopg3/), [Alembic](https://alembic.sqlalchemy.org/) |
| **Authentication** | [PyJWT](https://pyjwt.readthedocs.io/), [pwdlib (Argon2)](https://frankie567.github.io/pwdlib/), Python `secrets` & `hashlib` |
| **Cloud Services** | [AWS S3](https://aws.amazon.com/s3/) (via [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)), [Pillow (PIL)](https://pillow.readthedocs.io/) |
| **Email Service** | [aiosmtplib](https://aiosmtplib.readthedocs.io/), Jinja2 Email Templates |
| **Testing Suite** | [pytest](https://docs.pytest.org/), [AnyIO](https://anyio.readthedocs.io/), [HTTPX](https://www.python-httpx.org/), [Moto](https://docs.getmoto.org/) (AWS Mocking) |
| **Deployment & Infra** | Ubuntu 24.04 LTS (Azure VM), [Nginx](https://nginx.org/), [Systemd](https://systemd.io/), [Certbot (Let's Encrypt)](https://certbot.eff.org/), [Fail2ban](https://www.fail2ban.org/), UFW |

---

## 🌐 Production Deployment & Infrastructure

> [!NOTE]
> Deployed on an **Azure Linux Virtual Machine (Ubuntu 24.04 LTS)** with production-grade reverse proxying, SSL/TLS termination, automated process supervision, and perimeter firewall hardening.

### 1. Reverse Proxy & SSL (Nginx + Let's Encrypt)
- **High-Performance Reverse Proxy:** Nginx acts as the public-facing entry point, terminating SSL/TLS and reverse-proxying incoming requests to the local Uvicorn ASGI server on `127.0.0.1:8000`.
- **Static Asset Offloading:** Static assets (`/static/`) are served directly by Nginx with `Cache-Control: public, immutable` (30-day cache) to bypass application workers.
- **SSL/TLS & Security Headers:** Automated SSL certificate generation and auto-renewal via Certbot with HTTP/2 enabled. Includes automatic HTTP-to-HTTPS (301) redirection, `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and HTTP Strict Transport Security (HSTS) with a 2-year `max-age` and preload.
- **Upload Size Guard:** Configured `client_max_body_size 5M` at the Nginx edge to match the application's maximum permitted avatar upload size.

![SSL Certificate Verification](resource/showing_ssl_lock.png)
![Live Deployment on Azure VM](resource/fastapi-deployed.png)

---

### 2. Process Supervision (Systemd)
- **Reliable Daemonization:** Managed through a custom systemd service ([deployment/fastapi-blog.service](deployment/fastapi-blog.service)), ensuring the application runs continuously in the background and restarts automatically on system boot or unexpected process failure.
- **Process Isolation & Safety:** Runs under a dedicated unprivileged user (`shreyash-dhoot`) and group (`www-data`).
- **Production ASGI Server:** Executes FastAPI in multi-worker mode with `--proxy-headers` to ensure accurate client IP and protocol forwarding through Nginx.

```ini
[Unit]
Description = Fastapi Blog Application
After = network.target postgresql.service
Wants = postgresql.service

[Service]
User=shreyash-dhoot
Group=www-data
WorkingDirectory=/var/www/fastapi-blog
Environment="PATH=/var/www/fastapi-blog/venv/bin"
EnvironmentFile=/var/www/fastapi-blog/.env
ExecStart=/var/www/fastapi-blog/venv/bin/fastapi run --workers 2 --host 127.0.0.1 --port 8000 --proxy-headers
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

![Systemd Service Configuration](resource/systemd-service-file.png)

---

### 3. Server Security & Hardening (UFW & Fail2ban)
- **UFW (Uncomplicated Firewall):** Configured with a default deny ingress policy. Only essential network ports are explicitly allowed:
  - Port `22/tcp` (SSH management)
  - Port `80/tcp` (HTTP traffic & ACME challenge validation)
  - Port `443/tcp` (Encrypted HTTPS traffic)
- **Intrusion Prevention with Fail2ban:** Monitors SSH authentication logs and blocks suspicious IP addresses exhibiting repeated failed login attempts, guarding the server against automated brute-force bots and port scans.

![Fail2ban Security Jail](resource/fail2ban.png)

---

## 🧪 Automated Testing Suite

The repository includes a comprehensive, asynchronous test suite covering authentication, access control rules, CRUD endpoints, and file upload flows:

- **Isolated Database Transactions:** Tests execute against a test PostgreSQL instance using transactional savepoints rolled back after every test run, guaranteeing zero test state pollution.
- **Cloud S3 Mocking with Moto:** AWS S3 interactions are mocked in-memory using `moto.mock_aws`, enabling rapid, completely free, and deterministic unit/integration testing without network dependencies.
- **Async Client:** Powered by `httpx.AsyncClient` paired with `ASGITransport`.

Execute the test suite locally:

```bash
pytest tests/ -v
```

```text
tests/test_posts.py::test_get_posts_empty PASSED
tests/test_posts.py::test_create_post_authenticated PASSED
tests/test_posts.py::test_create_post_unauthenticated PASSED
tests/test_posts.py::test_update_post_author_only PASSED
tests/test_posts.py::test_delete_post_forbidden_for_non_author PASSED
tests/test_users.py::test_register_user_success PASSED
tests/test_users.py::test_login_and_jwt_issuance PASSED
tests/test_users.py::test_profile_picture_upload_mocked_s3 PASSED
============================= 12 passed in 3.20s ==============================
```

---

## 💻 Local Development Setup

Follow these steps to run the application locally on your workstation:

### 1. Clone the repository
```bash
git clone https://github.com/ShreyashDhoot/fastapi-production-blog.git
cd fastapi-production-blog
```

### 2. Set up a virtual environment

- **Windows (PowerShell):**
  ```powershell
  python -m venv fastapi-venv
  .\fastapi-venv\Scripts\Activate.ps1
  ```

- **Linux / macOS:**
  ```bash
  python3 -m venv fastapi-venv
  source fastapi-venv/bin/activate
  ```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create your local `.env` configuration file from the template:

```bash
cp .env.example .env
```

Ensure your `.env` contains the required parameters:

```env
# Database Configuration (PostgreSQL with psycopg v3 async driver)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/blog_db

# Security & Authentication (JWT & Argon2)
SECRET_KEY=generate_a_secure_random_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
RESET_TOKEN_EXPIRE_MINUTES=5

# Application Settings
FRONTEND_URL=http://localhost:8000
POST_PER_PAGE=10
MAX_UPLOAD_SIZE_BYTES=5242880

# Email Configuration (SMTP / Mailtrap / SendGrid / SES)
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

### 5. Run Database Migrations & Seed Demo Data

Apply Alembic migrations to set up the database schema:

```bash
alembic upgrade head
```

*(Optional)* Seed sample users, profile avatars, and blog posts:

```bash
python populate_db.py
```

*(Optional)* Verify your Amazon S3 bucket connectivity:

```bash
python check_s3.py
```

### 6. Run the Application

Start the local development server:

```bash
fastapi dev main.py
```
*(or via Uvicorn: `uvicorn main:app --reload`)*

- **Web Interface:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 📡 Key API Endpoints

### Authentication & User Management (`/api/users`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|:---:|
| `POST` | `/api/users/` | Register a new user | No |
| `POST` | `/api/users/token` | OAuth2 password login (issues JWT) | No |
| `GET` | `/api/users/me` | Retrieve profile of the authenticated user | **Yes** |
| `PATCH`| `/api/users/me` | Update username or email | **Yes** |
| `DELETE`| `/api/users/me` | Delete authenticated user account | **Yes** |
| `POST` | `/api/users/me/profile-picture` | Upload & resize avatar to AWS S3 | **Yes** |
| `DELETE`| `/api/users/me/profile-picture` | Delete avatar from AWS S3 (revert to default) | **Yes** |
| `POST` | `/api/users/change-password` | Update user password | **Yes** |
| `POST` | `/api/users/forgot-password` | Request password reset token via email | No |
| `POST` | `/api/users/reset-password` | Set new password with email token | No |
| `GET` | `/api/users/{user_id}` | Public profile info by User ID | No |
| `GET` | `/api/users/{user_id}/posts` | List paginated posts by author ID | No |

### Blog Posts (`/api/posts`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|:---:|
| `GET` | `/api/posts/` | List all posts (with `skip` & `limit` query parameters) | No |
| `POST` | `/api/posts/` | Create a new blog post | **Yes** |
| `GET` | `/api/posts/{post_id}` | Retrieve specific post details | No |
| `PUT` | `/api/posts/{post_id}` | Full update of an existing post | **Yes (Author)** |
| `PATCH`| `/api/posts/{post_id}` | Partial update of an existing post | **Yes (Author)** |
| `DELETE`| `/api/posts/{post_id}` | Delete a blog post | **Yes (Author)** |

---

## 🪟 Windows Async Event Loop Note

On Windows, Python 3.8+ defaults to `ProactorEventLoop`. However, `psycopg` (v3 async engine) requires a selector event loop (`SelectorEventLoop`).

This repository already configures `asyncio.WindowsSelectorEventLoopPolicy()` in:
- [alembic/env.py](alembic/env.py)
- [populate_db.py](populate_db.py)
- [tests/conftest.py](tests/conftest.py)

If you create standalone async scripts on Windows that interact with PostgreSQL via `psycopg`, include this block before running `asyncio.run()`:

```python
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

---

## 📄 License

This project is open-source and distributed under the [MIT License](LICENSE).
