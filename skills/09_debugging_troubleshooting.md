# Skill: Debugging & Troubleshooting

## Overview
Common issues, their root causes, and fixes for the VeggaFresh Django backend.

---

## 1. Quick Diagnostic Commands

```bash
cd svv_store

# Check for migration issues
python manage.py showmigrations

# Check Django setup is valid
python manage.py check

# Open Django shell for manual debugging
python manage.py shell

# Check DB connection
python manage.py dbshell
```

---

## 2. Common Issues & Fixes

### ❌ "No module named 'phonepe'"

**Cause:** PhonePe SDK not installed from private index.

**Fix:**
```bash
pip install -r requirements.txt
```

Ensure requirements.txt includes:
```
--index-url https://phonepe.mycloudrepo.io/public/repositories/phonepe-pg-sdk-python
--extra-index-url https://pypi.org/simple
phonepe_sdk
```

---

### ❌ "settings.SECRET_KEY is empty / None"

**Cause:** `.env` file not found or not loaded.

**Fix:**
```bash
# Check .env exists
ls svv_store/.env

# If not, create from sample
cp svv_store/sample_env.txt svv_store/.env
# Fill in SECRET_KEY and DB credentials
```

---

### ❌ `OperationalError: could not connect to server`

**Cause:** PostgreSQL not running or wrong credentials.

**Fix:**
1. Check `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` in `.env`
2. Ensure PostgreSQL is running
3. Test connection: `python manage.py dbshell`

---

### ❌ `ProgrammingError: relation "<table>" does not exist`

**Cause:** Migrations not applied.

**Fix:**
```bash
python manage.py migrate
```

If still failing:
```bash
python manage.py migrate --run-syncdb
```

---

### ❌ Cart total not updating after adding items

**Cause:** `cart.calculate_totals()` not called after mutation.

**Fix:** Always call after add/remove:
```python
item.save()
cart.calculate_totals()  # ← Required!
```

---

### ❌ Wishlist not reflecting new items

**Cause:** Redis cache not invalidated after update.

**Fix:**
```python
from django.core.cache import cache
cache.delete(f"user_wishlist_{user.id}")
```

---

### ❌ Product list not updating (cached)

**Cause:** `product_list_cache` Redis key still active (5-min TTL).

**Fix:** Manually invalidate:
```python
from django.core.cache import cache
cache.delete('product_list_cache')
```

Or wait 5 minutes for TTL to expire.

---

### ❌ OTP not being received (SMS)

**Debug steps:**
1. Check if number is in `OTP_BYPASS_MOBILES` (env) — bypass numbers never get SMS
2. Verify SMS credentials in `.env`: `SMS_USERNAME`, `SMS_PASSWORD`, `SMS_SENDER_ID`
3. Check `SMS_OTP_ENTITYID` and `SMS_OTP_TPID` are correct DLT registered values
4. Add logging to `users/services.py` to print API response

```python
response = requests.post(settings.SMS_API_URL, data=payload, timeout=5)
print(f"SMS API response: {response.status_code} — {response.text}")
```

---

### ❌ PhonePe payment not working

**Checklist:**
1. Are `PHONEPE_CLIENT_ID`, `PHONEPE_CLIENT_SECRET` set in `.env`?
2. Are you using `Env.SANDBOX` for testing and `Env.PRODUCTION` for live?
3. Is `PHONEPE_REDIRECT_URL` a valid HTTPS URL accessible from PhonePe?
4. Does the callback URL (`/api/v1/payment/callback/`) return HTTP 200?

---

### ❌ CORS error in frontend

**Current setting:** `CORS_ALLOW_ALL_ORIGINS = True` (open for all origins)

If CORS is blocked, check:
- `corsheaders.middleware.CorsMiddleware` is first in `MIDDLEWARE`
- For production, restrict origins:
```python
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://veggafresh.com",
    "https://admin.veggafresh.com",
]
```

---

### ❌ Django Admin login failing

**Cause:** Custom auth backend `EmailOrMobileModelBackend` requires mobile as the username by default.

**Fix:** Log in with mobile number (not email or username) in the Django admin login page.

Alternative: Use a superuser created with:
```bash
python manage.py createsuperuser
```

---

### ❌ JWT token expired errors

**Token lifetimes:**
- Access token: 60 minutes
- Refresh token: 1 day

**Fix:** Use token refresh endpoint:
```
POST /api/v1/token/refresh/
{ "refresh": "<refresh_token>" }
```

If refresh also expired, user must log in again.

---

### ❌ Category delete not working (returns 400)

**Cause:** Category has linked products and `?confirm=true` was not appended.

**Fix:**
```bash
DELETE /api/v1/categories/<id>/?confirm=true
```

---

### ❌ Product image upload failing

**Cause:** May be `MEDIA_ROOT` directory doesn't exist, or file permissions issue.

**Fix:**
```bash
mkdir -p svv_store/media
```

And ensure `settings.py` has:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

---

## 3. Debugging in Django Shell

```python
# Open shell
python manage.py shell

# Check a user
from users.models import User
u = User.objects.get(mobile="9876543210")
print(u.role, u.profile_complete, u.is_mobile_verified)

# Check cart
from cart.models import Cart
c = Cart.objects.get(user=u)
print(c.final_amount, c.items.count())

# Check orders
from orders.models import Order
orders = Order.objects.filter(user=u).order_by('-created_at')
print(orders.values('order_id', 'status__name'))

# Check cache
from django.core.cache import cache
print(cache.get('product_list_cache'))
cache.clear()  # Clear all cache (use carefully)
```

---

## 4. Log Files

Django logs to stdout/stderr by default. In production via Docker, check container logs:

```bash
docker logs <container_name>
```

For structured logging, add to `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

---

## 5. Production Checklist

| Item | Current | Should Be |
|------|---------|-----------|
| `DEBUG` | `True` | `False` |
| `ALLOWED_HOSTS` | `['*']` | Specific domain |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | `False` + specific origins |
| PhonePe `Env` | `Env.SANDBOX` | `Env.PRODUCTION` |
| `SECRET_KEY` | From `.env` ✅ | Strong random value |
| HTTPS | Configured via proxy ✅ | SSL certificate |
