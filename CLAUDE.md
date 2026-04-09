# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VeggaFresh Backend is a Django REST Framework e-commerce API for an online vegetable/produce store. The Django project root is `svv_store/` — run all `manage.py` commands from there.

## Commands

```bash
# Development server
cd svv_store && python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate

# Tests
python manage.py test                    # all tests
python manage.py test users              # single app
python manage.py test orders.tests.TestOrderAPI  # single test

# Static files (production)
python manage.py collectstatic --noinput
```

**Environment setup:** Copy `svv_store/sample_env.txt` to `svv_store/.env` and fill in values. Required vars: `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

**Docker deployment:** `./svv_store/deploy-scripts/deploy.sh main`

## Architecture

### Apps

| App | Responsibility |
|-----|---------------|
| `users` | Custom User model, JWT auth, OTP login, admin/employee roles |
| `categories` | Category → SubCategory hierarchy |
| `products` | Product catalog with CKEditor rich text, image uploads, filtering |
| `orders` | Order lifecycle, analytics, PDF report generation |
| `payments` | PhonePe SDK integration, payment status tracking |
| `cart` | Shopping cart and cart items |
| `address` | User delivery addresses |
| `wishlist` | Saved products per user |
| `utils` | Shared: pagination, renderers, PhonePe utils, PDF generator, signed URLs |

### URL Structure

All API routes are under `/api/v1/`. Special route: `/download/` → `SecureFileDownloadView`.

### Authentication

- Custom user model (`users.User`) with `email` (unique) and `mobile` (unique) fields; `role` is one of `SUPER_ADMIN`, `ADMIN`, `USER`.
- Auth backend: `users.backends.EmailOrMobileModelBackend` — accepts either email or mobile as identifier.
- JWT via `djangorestframework-simplejwt`: 60-min access tokens, 1-day refresh tokens with rotation and blacklisting.
- OTP flow: 6-digit codes, 5-minute expiry, delivered via BulkSMS Hyderabad.
- Views split by role: `views/user_views.py`, `views/admin_views.py`, `views/employee_views.py`.

### API Response Format

All responses go through `utils.renderers.CustomRenderer` — always use this renderer; don't return raw DRF responses without it.

Pagination is handled by `utils.pagination.CustomPageNumberPagination`.

### Key Integrations

- **PhonePe:** `utils/phonepe_utils.py` + `payments/views.py`; uses `phonepe_sdk` (custom index in requirements.txt)
- **PDF reports:** `utils/report_generator.py` using ReportLab; exposed via `orders/views/report_export.py`
- **Secure downloads:** `utils/signed_url.py` using `itsdangerous`
- **Cache:** Redis (redis-cloud); configured in `settings.py`
- **Rich text:** `django-ckeditor` for product descriptions

### Settings

`svv_store/svv_store/settings.py` — all secrets loaded from `.env` via `python-dotenv`. Database is PostgreSQL (`psycopg2-binary`). CORS is open (`CORS_ALLOW_ALL_ORIGINS = True`) in current config.
