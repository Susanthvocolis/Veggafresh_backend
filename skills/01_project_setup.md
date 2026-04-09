# Skill: Project Setup & Environment Configuration

## Overview
VeggaFresh Backend is a **Django REST Framework** e-commerce API for an online vegetable/produce store.
- Django project root: `svv_store/`
- Python version: 3.x
- Database: PostgreSQL
- Cache: Redis (Redis Cloud)

---

## 1. Clone & Install

```bash
git clone <repo-url>
cd Veggafresh_backend/svv_store
pip install -r requirements.txt
```

> **Note:** PhonePe SDK uses a private index — `requirements.txt` already handles this via `--index-url`.

---

## 2. Environment Variables

Copy the sample env file and fill in values:

```bash
cp svv_store/sample_env.txt svv_store/.env
```

### Required Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL user |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Database host |
| `DB_PORT` | Database port (default: 5432) |

### Optional / Integration Variables

| Variable | Description |
|----------|-------------|
| `OTP_BYPASS_MOBILES` | Comma-separated mobile numbers that skip OTP (any OTP accepted) |
| `SMS_API_URL` | BulkSMS API endpoint (connectbind.com) |
| `SMS_USERNAME` | SMS service username |
| `SMS_PASSWORD` | SMS service password |
| `SMS_SENDER_ID` | SMS sender ID |
| `SMS_TMID` | SMS template manager ID |
| `SMS_OTP_ENTITYID` / `SMS_OTP_TPID` | OTP SMS DLT registration IDs |
| `SMS_ORDER_ENTITYID` / `SMS_ORDER_TPID` | Order placed SMS DLT IDs |
| `SMS_DELIVERY_ENTITYID` / `SMS_DELIVERY_TPID` | Out-for-delivery SMS DLT IDs |
| `EMAIL_ADDRESS` | Gmail account for email sending |
| `EMAIL_PASSWORD` | Gmail app password |
| `PHONEPE_MERCHANT_ID` | PhonePe merchant ID |
| `PHONEPE_CLIENT_ID` | PhonePe client ID |
| `PHONEPE_CLIENT_SECRET` | PhonePe client secret |
| `PHONEPE_BASE_URL` | PhonePe API base URL |
| `PHONEPE_REDIRECT_URL` | Frontend redirect URL after payment |

---

## 3. Database Setup

```bash
cd svv_store
python manage.py migrate
```

### Create Superuser

```bash
python manage.py createsuperuser
```

> The custom user model (`users.User`) uses **mobile** as `USERNAME_FIELD`. Provide mobile, username, email, and password.

---

## 4. Run Dev Server

```bash
cd svv_store
python manage.py runserver
```

API available at: `http://127.0.0.1:8000/api/v1/`  
Admin panel: `http://127.0.0.1:8000/admin/`

---

## 5. Docker Deployment

```bash
./svv_store/deploy-scripts/deploy.sh main
```

See `svv_store/Dockerfile` for container configuration.

---

## 6. Installed Apps (in order)

```
django.contrib.*  → core Django
django_filters    → query param filtering
rest_framework    → DRF
rest_framework_simplejwt + token_blacklist → JWT auth
ckeditor          → rich text product descriptions
corsheaders       → CORS (currently open: CORS_ALLOW_ALL_ORIGINS=True)
users / categories / products / orders / payments / cart / address / wishlist
```

---

## 7. Key Settings at a Glance

| Setting | Value |
|---------|-------|
| `DEBUG` | `True` (change for production) |
| `ALLOWED_HOSTS` | `['*']` (restrict in production) |
| `AUTH_USER_MODEL` | `users.User` |
| `DEFAULT_RENDERER_CLASSES` | `utils.renderers.CustomRenderer` |
| `DEFAULT_PAGINATION_CLASS` | `utils.pagination.CustomPageNumberPagination` |
| JWT Access Token Lifetime | 60 minutes |
| JWT Refresh Token Lifetime | 1 day (rotation + blacklisting enabled) |
| OTP Expiry | 5 minutes (10 min in model — check `OTP_EXPIRY_MINUTES`) |
| OTP Length | 6 digits |
| Media Root | `svv_store/media/` |
| Cache Backend | Redis (django-redis) |
