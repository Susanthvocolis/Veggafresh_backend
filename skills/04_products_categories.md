# Skill: Products & Categories Management

## Overview
Products are the core catalog of VeggaFresh. Products belong to a **Category → SubCategory** hierarchy and have multiple **variants** (size/weight/unit combinations) and **images**.

---

## 1. Data Models

### Category (db_table: `category`)

| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField | Category name |
| `image` | ImageField | Category image |
| `created_by` | FK → User | Auto-set on create |
| `updated_by` | FK → User | Auto-set on update |
| `created_at` | DateTimeField | Auto |
| `updated_at` | DateTimeField | Auto |

### SubCategory (db_table: `subcategory`)

| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField | SubCategory name |
| `category` | FK → Category | Parent category |
| `image` | ImageField | SubCategory image |
| `created_by` | FK → User | Auto-set |
| `updated_by` | FK → User | Auto-set |

### Product (db_table: `product`)

| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField(255) | Product name |
| `slug` | SlugField(unique) | Auto-generated from name on save |
| `description` | RichTextField | CKEditor rich HTML content |
| `category` | FK → Category | |
| `subcategory` | FK → SubCategory | |
| `brand` | CharField(100) | Optional brand name |
| `is_active` | BooleanField | Default True; soft-delete via category |
| `created_by` | FK → User | |
| `updated_by` | FK → User | |
| `created_at` / `updated_at` | DateTimeField | Auto |

### ProductVariant (db_table: `product_variant`)

| Field | Type | Notes |
|-------|------|-------|
| `product` | FK → Product | Parent product |
| `quantity` | DecimalField(5,2) | e.g., 500, 1.5 |
| `unit` | CharField | `kg`, `g`, `l`, `ml`, `pc` |
| `price` | DecimalField(10,2) | MRP price |
| `discounted_price` | DecimalField(10,2) | Sale price (nullable) |
| `stock` | PositiveIntegerField | Available units |
| `is_available` | BooleanField | Default True |

> **Unique constraint:** `(product, quantity, unit)` — no duplicate variant sizes per product.

### ProductImage (db_table: `product_image`)

| Field | Type | Notes |
|-------|------|-------|
| `product` | FK → Product | |
| `image` | TextField | Stored as file path/URL string |
| `alt_text` | CharField(255) | SEO alt text |

---

## 2. API Endpoints

### Categories (Admin)

```
GET    /api/v1/categories/           → List all
POST   /api/v1/categories/           → Create
GET    /api/v1/categories/<id>/      → Detail
PATCH  /api/v1/categories/<id>/      → Update
DELETE /api/v1/categories/<id>/      → Delete (see safety note)
```

#### Delete Safety
Deleting a category that has products:
1. First request returns a warning (400) with `confirm_url`
2. Second request with `?confirm=true` deletes the category and marks all linked products **inactive**

```
DELETE /api/v1/categories/<id>/?confirm=true
```

---

### SubCategories (Admin)

```
GET    /api/v1/subcategories/           → List all
POST   /api/v1/subcategories/           → Create
GET    /api/v1/subcategories/<id>/      → Detail
PATCH  /api/v1/subcategories/<id>/      → Update
DELETE /api/v1/subcategories/<id>/      → Delete
```

---

### Products (Admin)

```
GET    /api/v1/products/           → List (filter: ?is_active=true/false)
POST   /api/v1/products/           → Create (multipart/form-data)
GET    /api/v1/products/<id>/      → Detail
PATCH  /api/v1/products/<id>/      → Update
DELETE /api/v1/products/<id>/      → Delete
```

#### Create Product — `multipart/form-data` Format

```
name         = "Fresh Tomatoes"
slug         = "fresh-tomatoes"        (auto-generated if omitted)
description  = "<p>Rich HTML...</p>"
category     = 2
subcategory  = 5
brand        = "Organic Farm"
is_active    = true

variants     = '[{"quantity": 500, "unit": "g", "price": 30.00, "discounted_price": 25.00, "stock": 100}]'
              (JSON string of array)

images       = <file1>, <file2>        (multi-file upload)
alt_text     = "Tomato front view"     (positional per image)
```

> **Important:** `variants` must be a **JSON string** (not nested JSON), because it's sent in multipart form.

---

### Product Variants (Admin)

```
GET    /api/v1/variants/           → List all variants
POST   /api/v1/variants/           → Create variant
GET    /api/v1/variants/<id>/      → Detail
PATCH  /api/v1/variants/<id>/      → Update variant (price, stock, is_available)
DELETE /api/v1/variants/<id>/      → Delete variant
```

---

### User-Facing Products (Public)

```
GET /api/v1/user-products/
```

#### Query Parameters

| Param | Type | Example | Description |
|-------|------|---------|-------------|
| `is_active` | bool | `true` | Filter by active status (default: active only) |
| `category` | int | `2` | Category ID |
| `subcategory` | int | `5` | SubCategory ID |
| `brand` | string | `"organic"` | Case-insensitive brand filter |
| `search` | string | `"tomato"` | Searches: name, slug, category name, subcategory name |
| `page` | int | `2` | Page number |
| `page_size` | int | `20` | Items per page (max: 100, default: 10) |

> Response is **cached for 5 minutes** (`product_list_cache`). Cache is NOT invalidated on product save — clear manually if needed.

---

### Secure Media

```
GET /api/v1/secure-media/<token>/
```

Serves product images via signed URL tokens. Token generated by `utils.signed_url` using `itsdangerous`. Requires `ImageViewPermission`.

---

## 3. Permissions

| Endpoint Group | Permission Class |
|----------------|-----------------|
| Categories | `IsSuperAdminOrHasCategoryPermission` |
| Products & Variants | `IsSuperAdminOrHasProductPermission` |
| User Products | Open (no auth required) |
| Secure Media | `ImageViewPermission` |

---

## 4. Common Tasks

### Add a New Product with Variants (cURL example)

```bash
curl -X POST http://localhost:8000/api/v1/products/ \
  -H "Authorization: Bearer <token>" \
  -F "name=Fresh Spinach" \
  -F "category=1" \
  -F "subcategory=3" \
  -F 'variants=[{"quantity": 250, "unit": "g", "price": 20.00, "stock": 50}]' \
  -F "images=@/path/to/spinach.jpg" \
  -F "alt_text=Fresh Spinach Pack"
```

### Update Stock Only (variant patch)

```bash
curl -X PATCH http://localhost:8000/api/v1/variants/7/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"stock": 200, "is_available": true}'
```

### Soft-Delete a Product

Set `is_active=false` instead of deleting:

```bash
curl -X PATCH http://localhost:8000/api/v1/products/5/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

---

## 5. Slug Auto-Generation

`Product.save()` auto-generates slug from name using `django.utils.text.slugify`:

```python
self.slug = slugify(self.name)
```

This triggers on:
- New product creation
- When `name` changes on update

If you need a custom slug, pass it explicitly in the request payload.
