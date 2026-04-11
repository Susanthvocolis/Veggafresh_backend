# Skills Index — VeggaFresh Backend

This folder contains skill files that document how to work with the **VeggaFresh Backend** Django REST API project. Each file covers a specific domain or task.

---

## 📂 Skill Files

| File | Topic | Key Contents |
|------|-------|--------------|
| [01_project_setup.md](./01_project_setup.md) | Project Setup & Environment | Install, `.env` vars, dev server, Docker, settings overview |
| [02_authentication.md](./02_authentication.md) | Auth & User Management | OTP flow, JWT, admin login, module permissions, employee CRUD |
| [03_adding_new_endpoint.md](./03_adding_new_endpoint.md) | Adding New API Endpoints | View patterns, URL registration, filtering, caching, testing |
| [04_products_categories.md](./04_products_categories.md) | Products & Categories | Models, CRUD, multipart upload, variant management, user products |
| [05_orders_payments.md](./05_orders_payments.md) | Orders & Payments | PhonePe flow, COD flow, order status lifecycle, analytics, delivery |
| [06_cart_wishlist_address.md](./06_cart_wishlist_address.md) | Cart, Wishlist & Address | Cart CRUD, wishlist caching, address auto-default, admin address APIs |
| [07_sms_email_notifications.md](./07_sms_email_notifications.md) | SMS, Email & Notifications | BulkSMS integration, OTP bypass, adding new SMS types, signed URLs |
| [08_migrations_models_database.md](./08_migrations_models_database.md) | Migrations, Models & Database | Migration workflow, ORM patterns, Redis cache, admin registration |
| [09_debugging_troubleshooting.md](./09_debugging_troubleshooting.md) | Debugging & Troubleshooting | Common errors, fixes, shell debugging, production checklist |
| [10_git_workflow.md](./10_git_workflow.md) | Git Workflow & Branch Management | Branch naming, commit format, never push to main, reverting commits |
| [15_optimization_checklist.md](./15_optimization_checklist.md) | ⚡ Optimization Checklist | Mandatory patterns for all new files: select_related, prefetch_related, cache, pagination, etc. |

---

## 🏗️ Project Architecture Summary

```
Veggafresh_backend/
└── svv_store/              ← Django project root (run manage.py from here)
    ├── svv_store/          ← Core settings, URLs, WSGI/ASGI
    ├── users/              ← Custom User, JWT, OTP, roles, permissions
    ├── categories/         ← Category → SubCategory hierarchy
    ├── products/           ← Product catalog, variants, images
    ├── orders/             ← Order lifecycle, analytics, PDF reports
    ├── payments/           ← PhonePe + COD payment flows
    ├── cart/               ← Shopping cart
    ├── address/            ← Delivery addresses
    ├── wishlist/           ← Saved products
    └── utils/              ← Shared: renderer, pagination, signed URLs, PDF gen
```

---

## 🔑 Key Conventions

- **All APIs** → `/api/v1/`
- **Auth** → JWT Bearer Token (`Authorization: Bearer <token>`)
- **Custom Renderer** → `utils.renderers.CustomRenderer` (always wraps responses)
- **Pagination** → `utils.pagination.CustomPageNumberPagination`
- **Cache** → Redis (django-redis), 5-min TTL for products & wishlist
- **Roles** → `SUPER_ADMIN` (full access) > `ADMIN` (module-gated) > `USER` (customer)
- **DB** → PostgreSQL, explicit `db_table`, indexed FK fields

---

## 🚀 Quick Start

```bash
cd Veggafresh_backend/svv_store
cp sample_env.txt .env    # fill in DB + secrets
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

API Base: `http://127.0.0.1:8000/api/v1/`
