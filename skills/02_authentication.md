# Skill: Authentication & User Management

## Overview
VeggaFresh uses a **custom User model** with dual-identifier support (mobile or email) and two auth flows:
1. **OTP-based login** — for end customers (mobile/email OTP)
2. **Password-based login** — for admin/employee panel access

---

## 1. Custom User Model (`users.User`)

```
Model: users.User  (db_table: 'user')
Auth Backend: users.backends.EmailOrMobileModelBackend
```

### Fields

| Field | Type | Notes |
|-------|------|-------|
| `mobile` | CharField(15, unique) | `USERNAME_FIELD` — primary login key |
| `email` | EmailField(unique) | Also used for login |
| `first_name` | CharField | Optional |
| `username` | CharField | Not unique; optional |
| `role` | CharField | `SUPER_ADMIN` / `ADMIN` / `USER` |
| `is_mobile_verified` | BooleanField | Set True after OTP verify |
| `is_email_verified` | BooleanField | Set True after OTP verify |
| `profile_complete` | BooleanField | Set True after profile patch |
| `date_of_birth` | DateField | Optional |
| `address` | TextField | Legacy plain-text address (not delivery address) |

### Roles

| Role | Constant | Access Level |
|------|----------|--------------|
| Super Admin | `User.Role.SUPER_ADMIN` | Full access — no restrictions |
| Admin / Employee | `User.Role.ADMIN` | Per-module permission gated |
| Customer | `User.Role.USER` | User-facing APIs only |

---

## 2. OTP Flow (End-User Authentication)

### Step 1 — Request OTP

```
POST /api/v1/request-otp/
```

```json
// via mobile
{ "identifier": "9876543210", "identifier_type": "mobile" }

// via email
{ "identifier": "user@example.com", "identifier_type": "email" }
```

**What happens:**
- Creates/gets user by mobile or email
- If mobile is in `OTP_BYPASS_MOBILES` (from `.env`) → skips OTP creation, returns success immediately
- Otherwise generates 6-digit OTP (5-min expiry), sends via SMS/email

---

### Step 2 — Verify OTP

```
POST /api/v1/verify-otp/
```

```json
{ "identifier": "9876543210", "otp": "123456", "identifier_type": "mobile" }
```

**Response:**

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "is_verified": true,
  "profile_complete": false
}
```

**What happens:**
- Validates OTP (not used, not expired)
- Marks OTP as used, marks user as verified
- Returns JWT tokens

---

### Step 3 — Complete Profile (if `profile_complete: false`)

```
PATCH /api/v1/complete-profile/
Authorization: Bearer <access_token>
```

```json
{
  "first_name": "Ravi",
  "email": "ravi@example.com",
  "date_of_birth": "1995-06-15"
}
```

Sets `profile_complete = True` automatically on save.

---

## 3. Admin / Employee Login (Password-based)

```
POST /api/v1/login/
```

```json
{ "username": "admin@example.com", "password": "secret123" }
```

- Accepts email or mobile as `username` (via `EmailOrMobileModelBackend`)
- Only allows `SUPER_ADMIN` and `ADMIN` roles
- Returns `permissions` object for `ADMIN` role users

**Response:**

```json
{
  "access": "<token>",
  "refresh": "<token>",
  "user": {
    "id": 1,
    "mobile": "9876543210",
    "email": "admin@example.com",
    "role": "ADMIN",
    "is_superadmin": false,
    "permissions": {
      "can_add_product": true,
      "can_edit_product": false,
      ...
    }
  }
}
```

---

## 4. JWT Token Refresh

```
POST /api/v1/token/refresh/
```

```json
{ "refresh": "<refresh_token>" }
```

- Returns new `access` token
- Rotation enabled: old refresh token is blacklisted, new one issued

---

## 5. Module Permissions (`ModulePermission` model)

Each `ADMIN` user has one `ModulePermission` record (OneToOne).

### Permission Fields

| Module | Fields |
|--------|--------|
| Products | `can_add_product`, `can_edit_product`, `can_delete_product`, `can_view_product` |
| Categories | `can_add_category`, `can_view_category`, `can_edit_category`, `can_delete_category` |
| Sub-Categories | `can_add_subcategory`, `can_view_subcategory`, `can_edit_subcategory`, `can_delete_subcategory` |
| Orders | `can_manage_orders`, `can_manage_delivery_status` |
| Payments | `can_view_payment` |
| Users | `can_view_users`, `can_update_users`, `can_delete_users` |

> **Note:** `SUPER_ADMIN` users bypass all permission checks. Only `ADMIN` users are subject to module-level restrictions.

---

## 6. Employee Management (Super-Admin only)

```
GET    /api/v1/employees/          → List employees
POST   /api/v1/employees/create/   → Create employee
GET    /api/v1/employees/<id>/     → Get employee detail
PATCH  /api/v1/employees/<id>/     → Update employee
DELETE /api/v1/employees/<id>/     → Delete employee
GET    /api/v1/all-users/          → List all customers
```

All require `IsSuperAdmin` permission.

---

## 7. Adding a New Employee (Checklist)

1. Login as Super Admin → get access token
2. `POST /api/v1/employees/create/` with employee data (role=ADMIN, mobile, email, password)
3. Create `ModulePermission` for the employee via Django Admin or a custom endpoint
4. Employee logs in via `POST /api/v1/login/`

---

## 8. OTP Model (`users.OTP`)

```
db_table: 'otp'
```

| Field | Notes |
|-------|-------|
| `identifier` | Mobile number or email |
| `identifier_type` | `'mobile'` or `'email'` |
| `otp` | 6-digit string |
| `is_used` | Boolean — True after verification |
| `expired_at` | Auto-set to now + 10 min (model level) |
| `message_id` | SMS message ID for tracking |

`OTP.is_valid()` → returns `True` if `not is_used AND now <= expired_at`
