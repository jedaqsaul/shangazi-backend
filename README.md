# Shangazi Foundation — Backend API

Production-ready Flask backend for the Shangazi Foundation donation platform.
Handles M-Pesa STK Push donations, donor records, and secure admin management.

---

## Tech Stack

- **Framework:** Flask 3.0
- **Database:** PostgreSQL (production) / SQLite (development)
- **ORM:** SQLAlchemy + Flask-Migrate
- **Auth:** Flask-JWT-Extended
- **Payments:** Safaricom Daraja API (STK Push)
- **Server:** Gunicorn

---

## Project Structure

```
app/
├── config/          # Environment-specific configuration
├── models/          # SQLAlchemy database models
├── routes/          # URL registration (thin layer)
├── controllers/     # Request/response handling
├── services/        # Business logic (testable core)
├── middleware/       # JWT auth, rate limiting, validators
└── utils/           # Logger, helpers, error handlers
```

---

## Quick Start (Development)

### 1. Clone and create virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

Minimum required for development:
```env
FLASK_ENV=development
SECRET_KEY=any-random-string
JWT_SECRET_KEY=another-random-string
DATABASE_URL=sqlite:///shangazi_dev.db
```

For M-Pesa (get from Daraja Developer Portal):
```env
DARAJA_CONSUMER_KEY=...
DARAJA_CONSUMER_SECRET=...
DARAJA_SHORTCODE=174379          # Sandbox shortcode
DARAJA_PASSKEY=...               # From Daraja portal
DARAJA_CALLBACK_URL=https://your-ngrok-url.ngrok.io/api/daraja/callback
DARAJA_ENV=sandbox
```

### 3. Initialize database

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 4. Create super admin

```bash
flask seed-admin
```

### 5. Run development server

```bash
python run.py
```

Server runs at `http://localhost:5000`

---

## API Endpoints

### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/donations/initiate` | Start M-Pesa STK Push |
| GET | `/api/donations/status/<id>` | Poll payment status |
| POST | `/api/daraja/callback` | Safaricom callback (internal) |

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Admin login |
| POST | `/api/auth/logout` | Logout |
| POST | `/api/auth/refresh` | Refresh access token |

### Admin (JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/donations` | List donations (filterable) |
| GET | `/api/admin/donations/<id>` | Single donation |
| GET | `/api/admin/stats` | Dashboard statistics |
| GET | `/api/admin/export` | CSV export |
| GET | `/api/admin/audit-logs` | Audit trail (super_admin) |
| POST | `/api/admin/users` | Create admin user (super_admin) |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific suite
pytest tests/test_auth.py -v
pytest tests/test_donations.py -v
pytest tests/test_daraja.py -v
```

Import `Shangazi_Foundation_API.postman_collection.json` into Postman for manual testing.

---

## Testing Daraja Locally

Daraja needs a public HTTPS URL for callbacks. Use ngrok in development:

```bash
# Install ngrok, then:
ngrok http 5000

# Copy the https URL and set in .env:
DARAJA_CALLBACK_URL=https://abc123.ngrok.io/api/daraja/callback
```

**Sandbox flow:**
1. Call `POST /api/donations/initiate` with a Safaricom test number
2. Daraja sends STK Push to the test number
3. Accept/decline on the phone (or use Daraja sandbox simulator)
4. Daraja POSTs to your callback URL
5. Poll `GET /api/donations/status/<checkout_request_id>`

---

## Production Deployment

### 1. Set production environment variables

All variables from `.env.example` must be set in your hosting environment.

```bash
FLASK_ENV=production
DATABASE_URL=postgresql://user:pass@host:5432/shangazi_db
DARAJA_ENV=production
DARAJA_CALLBACK_URL=https://api.yourdomain.com/api/daraja/callback
FRONTEND_URL=https://yourdomain.com
```

### 2. Run database migrations

```bash
flask db upgrade
flask seed-admin
```

### 3. Start with Gunicorn

```bash
gunicorn wsgi:app \
  --workers 5 \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

Workers = (2 × CPU cores) + 1

### 4. Reverse proxy (Nginx recommended)

Configure Nginx to proxy `/api/*` to Gunicorn on port 5000.
Ensure HTTPS is enabled (required for Daraja callbacks).

---

## Security Checklist

- [ ] `SECRET_KEY` is a strong random value (not the example)
- [ ] `JWT_SECRET_KEY` is a strong random value
- [ ] `INITIAL_ADMIN_PASSWORD` changed after first login
- [ ] `FLASK_ENV=production` set
- [ ] HTTPS enabled on server
- [ ] `FRONTEND_URL` set to exact frontend domain (no wildcard)
- [ ] Daraja callback URL is HTTPS
- [ ] Database backups configured
- [ ] Log monitoring set up

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_ENV` | Yes | `development` or `production` |
| `SECRET_KEY` | Yes | Flask secret key |
| `JWT_SECRET_KEY` | Yes | JWT signing key |
| `DATABASE_URL` | Yes | Database connection string |
| `DARAJA_CONSUMER_KEY` | Yes | From Daraja developer portal |
| `DARAJA_CONSUMER_SECRET` | Yes | From Daraja developer portal |
| `DARAJA_SHORTCODE` | Yes | M-Pesa business shortcode |
| `DARAJA_PASSKEY` | Yes | STK Push passkey |
| `DARAJA_CALLBACK_URL` | Yes | Public HTTPS URL for callbacks |
| `DARAJA_ENV` | Yes | `sandbox` or `production` |
| `FRONTEND_URL` | Yes | React app URL for CORS |
| `INITIAL_ADMIN_EMAIL` | Seed | Super admin email |
| `INITIAL_ADMIN_PASSWORD` | Seed | Super admin password |
# shangazi-backend
