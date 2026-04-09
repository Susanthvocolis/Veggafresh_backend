# Skill: SMS, Email & Notification Services

## Overview
VeggaFresh sends transactional SMS notifications via **connectbind.com BulkSMS** API and email via **Gmail SMTP**. All SMS/email logic lives in `users/services.py`.

---

## 1. SMS Service (BulkSMS via connectbind.com)

### Configuration (settings.py)

```python
SMS_API_URL    = os.getenv("SMS_API_URL", "https://dstri.connectbind.com:8443/sendsms/bulksms")
SMS_USERNAME   = os.getenv("SMS_USERNAME", "")
SMS_PASSWORD   = os.getenv("SMS_PASSWORD", "")
SMS_SENDER_ID  = os.getenv("SMS_SENDER_ID", "")
SMS_TMID       = os.getenv("SMS_TMID", "")

# OTP SMS DLT registration
SMS_OTP_ENTITYID  = os.getenv("SMS_OTP_ENTITYID", "")
SMS_OTP_TPID      = os.getenv("SMS_OTP_TPID", "")

# Order placed SMS DLT registration
SMS_ORDER_ENTITYID = os.getenv("SMS_ORDER_ENTITYID", "")
SMS_ORDER_TPID     = os.getenv("SMS_ORDER_TPID", "")

# Out for delivery SMS DLT registration
SMS_DELIVERY_ENTITYID = os.getenv("SMS_DELIVERY_ENTITYID", "")
SMS_DELIVERY_TPID     = os.getenv("SMS_DELIVERY_TPID", "")
```

---

### SMS Functions (users/services.py)

#### 1. `create_or_update_otp(identifier, identifier_type, user)`

Creates/updates OTP and sends it via SMS or email.

```python
from users.services import create_or_update_otp

otp = create_or_update_otp(
    identifier="9876543210",
    identifier_type="mobile",  # or "email"
    user=user_instance
)
```

---

#### 2. `send_order_placed_sms(mobile, user_name, order_id, total_amount)`

Called automatically when:
- COD order is created (`payments/views.py: CodOrderCreateView`)

```python
from users.services import send_order_placed_sms

send_order_placed_sms(
    mobile="9876543210",
    user_name="Ravi",
    order_id="260409001",
    total_amount=450.00
)
```

---

#### 3. `send_out_for_delivery_sms(mobile, user_name, order_id)`

Called automatically when:
- Order status is updated to **"Out For Delivery"** (`orders/views/views.py: AdminOrderViewSet.update_status`)

```python
from users.services import send_out_for_delivery_sms

send_out_for_delivery_sms(
    mobile="9876543210",
    user_name="Ravi",
    order_id="260409001"
)
```

---

### SMS Trigger Map

| Event | Function | Where Called |
|-------|----------|--------------|
| OTP request | `create_or_update_otp()` | `users/views/user_views.py: RequestOTPView` |
| COD order placed | `send_order_placed_sms()` | `payments/views.py: CodOrderCreateView` |
| Order → Out For Delivery | `send_out_for_delivery_sms()` | `orders/views/views.py: AdminOrderViewSet.update_status` |

---

### OTP Bypass (Test Numbers)

Mobile numbers listed in `settings.OTP_BYPASS_MOBILES` (env: `OTP_BYPASS_MOBILES`):
- Skip OTP creation entirely on `request-otp`
- Accept **any OTP** on `verify-otp`
- No SMS sent

Default bypass number: `9999900000`

---

## 2. Email Service (Gmail SMTP)

### Configuration (settings.py)

```python
EMAIL_BACKEND      = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST         = 'smtp.gmail.com'
EMAIL_PORT         = 587
EMAIL_USE_TLS      = True
EMAIL_HOST_USER    = os.getenv('EMAIL_ADDRESS')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD')  # Use Gmail App Password
DEFAULT_FROM_EMAIL = "vamshiyvu@gmail.com"
```

> **Note:** Use a **Gmail App Password** (not your account password) generated from Google's security settings.

### Sending Email (Django built-in)

```python
from django.core.mail import send_mail

send_mail(
    subject='Your OTP Code',
    message='Your OTP is 123456. Valid for 5 minutes.',
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=['user@example.com'],
    fail_silently=False,
)
```

---

## 3. Adding a New SMS Notification

### Step 1 — Register DLT template with telecom

Get `ENTITYID` and `TPID` from the DLT portal.

### Step 2 — Add to settings

```python
# settings.py
SMS_MYEVENT_ENTITYID = os.getenv("SMS_MYEVENT_ENTITYID", "")
SMS_MYEVENT_TPID     = os.getenv("SMS_MYEVENT_TPID", "")
```

### Step 3 — Add to .env

```
SMS_MYEVENT_ENTITYID=your_entity_id
SMS_MYEVENT_TPID=your_tpid
```

### Step 4 — Create the service function

```python
# users/services.py
from django.conf import settings
import requests

def send_my_event_sms(mobile, user_name, extra_data):
    message = f"Hi {user_name}, your event happened! Details: {extra_data}. -VeggaFresh"
    
    payload = {
        "username": settings.SMS_USERNAME,
        "password": settings.SMS_PASSWORD,
        "sender": settings.SMS_SENDER_ID,
        "to": mobile,
        "message": message,
        "tmid": settings.SMS_TMID,
        "entityid": settings.SMS_MYEVENT_ENTITYID,
        "tpid": settings.SMS_MYEVENT_TPID,
    }
    
    try:
        response = requests.post(settings.SMS_API_URL, data=payload, timeout=5)
        return response
    except Exception as e:
        print(f"SMS send failed: {e}")
        return None
```

### Step 5 — Call it in your view

```python
from users.services import send_my_event_sms

if user.mobile:
    try:
        send_my_event_sms(
            mobile=user.mobile,
            user_name=user.first_name or "Customer",
            extra_data="some value"
        )
    except Exception as e:
        print(f"SMS failed: {e}")  # Never break the main flow for SMS failures
```

> **Important:** Always wrap SMS calls in `try/except` so a failed SMS never breaks the core business logic.

---

## 4. Signed URL (Secure Media Downloads)

Used for generating expiring URLs for report downloads and product images.

### `utils/signed_url.py`

```python
from utils.signed_url import generate_signed_token, verify_signed_token

# Generate a token (e.g., for a file path)
token = generate_signed_token("reports/sales_2024.pdf")

# Verify and get the original value
file_path = verify_signed_token(token)
```

Uses `itsdangerous` under the hood with the Django `SECRET_KEY`.

---

## 5. PDF Report Generation

### `utils/report_generator.py`

Uses **ReportLab** to generate PDF sales reports. Exposed via:

```
GET /api/v1/generate-sales-report/  → Triggers PDF generation, returns token
GET /download/?token=<t>&filename=<f>  → Securely downloads the file
```

The generated file is saved server-side and a signed download URL is returned to the admin.
