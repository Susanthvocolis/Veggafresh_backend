# Skill: Cart, Wishlist & Address Management

## Overview
These three apps handle the customer's shopping experience: saving products (wishlist), building an order (cart), and specifying delivery location (address).

---

## 1. Cart

### Models

**Cart** (db_table: `cart`)

| Field | Type | Notes |
|-------|------|-------|
| `user` | FK → User (OneToOne) | One cart per user |
| `total_amount` | DecimalField | Sum before discount |
| `final_amount` | DecimalField | After discount |
| `discount` | DecimalField | Total discount amount |

**CartItem** (db_table: `cart_item`)

| Field | Type | Notes |
|-------|------|-------|
| `cart` | FK → Cart | Parent cart |
| `product_variant` | FK → ProductVariant | Which variant |
| `quantity` | PositiveIntegerField | Quantity |

`cart.calculate_totals()` — call this after any add/remove to recalculate `total_amount`, `final_amount`, `discount`.

---

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/cart/` | Get user's cart (creates if none) |
| `POST` | `/api/v1/cart/` | Add or update item in cart |
| `DELETE` | `/api/v1/cart/<item_id>/` | Remove a single cart item |

All require `IsAuthenticated`.

---

### Add / Update Cart Item

```
POST /api/v1/cart/
Authorization: Bearer <token>
```

```json
{ "product_variant_id": 5, "quantity": 2 }
```

**Behaviour:**
- If item already exists → quantity is **overwritten** (not incremented)
- To increment, read current quantity first and add

**Response:**
```json
{
  "id": 1,
  "items": [
    {
      "id": 12,
      "product_variant": { "id": 5, "price": "30.00", "discounted_price": "25.00", ... },
      "quantity": 2
    }
  ],
  "total_amount": "60.00",
  "final_amount": "50.00",
  "discount": "10.00"
}
```

---

### Remove Cart Item

```
DELETE /api/v1/cart/<item_id>/
Authorization: Bearer <token>
```

Removes a specific item by its CartItem `id` (not variant ID).

---

### Cart Lifecycle (related to Orders)

When an order is placed (PhonePe or COD), the cart is **cleared** immediately:

```python
cart.items.all().delete()
cart.calculate_totals()
```

---

## 2. Wishlist

### Model

**Wishlist** (db_table: `wishlist`)

| Field | Type | Notes |
|-------|------|-------|
| `user` | FK → User | |
| `product` | FK → Product | Saved product |
| `created_at` | DateTimeField | Auto |

---

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/wishlist/` | List user's wishlist |
| `POST` | `/api/v1/wishlist/` | Add product to wishlist |
| `DELETE` | `/api/v1/wishlist-remove/<product_id>/` | Remove one product |
| `DELETE` | `/api/v1/wishlist-clear/` | Clear entire wishlist |

All require `IsAuthenticated`.

---

### Add to Wishlist

```
POST /api/v1/wishlist/
Authorization: Bearer <token>
```

```json
{ "product_id": 12 }
```

- If already in wishlist → returns `200 {"message": "Already in your wishlist."}`
- New addition → returns `201` with wishlist item data

---

### Wishlist Caching

Wishlist is cached per-user for **5 minutes**:

```python
cache_key = f"user_wishlist_{request.user.id}"
```

Cache is invalidated on every add or remove. The cache uses **Redis** (configured in `settings.CACHES`).

---

## 3. Address

### Model

**Address** (db_table: `address`)

| Field | Type | Notes |
|-------|------|-------|
| `user` | FK → User | Owner |
| `full_name` | CharField | Recipient name |
| `mobile` | CharField | Contact number |
| `house_no` | CharField | House/flat number |
| `street` | CharField | Street name |
| `city` | CharField | City |
| `state` | CharField | State |
| `pincode` | CharField | PIN code |
| `is_default` | BooleanField | Default delivery address |
| `created_at` | DateTimeField | Auto |

---

### User Address APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/address/` | List my addresses (default first) |
| `POST` | `/api/v1/address/` | Create new address |
| `GET` | `/api/v1/address/<id>/` | Get specific address |
| `PATCH` | `/api/v1/address/<id>/` | Update address |
| `DELETE` | `/api/v1/address/<id>/` | Delete address |
| `PATCH` | `/api/v1/address/<id>/set-default/` | Mark as default |

All require `IsAuthenticated`.

---

### Create Address

```
POST /api/v1/address/
Authorization: Bearer <token>
```

```json
{
  "full_name": "Ravi Kumar",
  "mobile": "9876543210",
  "house_no": "12A",
  "street": "MG Road",
  "city": "Hyderabad",
  "state": "Telangana",
  "pincode": "500001",
  "is_default": true
}
```

**Auto-default logic:**
- If the user's first address → automatically set as default
- If `is_default: true` → clears the previous default address first

---

### Set Default Address

```
PATCH /api/v1/address/<id>/set-default/
Authorization: Bearer <token>
```

No body needed. Clears all other defaults and sets this one.

---

### Delete Address

```
DELETE /api/v1/address/<id>/
Authorization: Bearer <token>
```

**Auto-reassign default:**
- If the deleted address was the default, the next most-recent address is automatically made default

---

### Admin Address APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/addresses/` | List all addresses |
| `GET` | `/api/v1/admin/addresses/<id>/` | Get any address detail |
| `DELETE` | `/api/v1/admin/addresses/<id>/` | Delete any address |

**Query Filters (admin list):**

```
?user_id=5         → addresses for a specific user
?city=Hyderabad    → case-insensitive city filter
?pincode=500001    → exact pincode filter
```

Requires `IsSuperAdminOrAdmin` permission.

---

## 4. Common Patterns

### Getting User's Default Address

```python
from address.models import Address

default_address = Address.objects.filter(user=user, is_default=True).first()
```

### Validate Address Before Order

Always validate the `address_id` belongs to the requesting user:

```python
try:
    address = Address.objects.get(id=address_id, user=user)
except Address.DoesNotExist:
    return Response({"error": "Address not found."}, status=404)
```

### Pre-fetching Cart Details

```python
from cart.models import Cart
from cart.serializers import CartSerializer

cart = Cart.objects.get(user=user)
if not cart.items.exists():
    return Response({"error": "Cart is empty."}, status=400)

cart_data = CartSerializer(cart).data
total = cart_data['final_amount']
```
