# Skill: Orders & Payments Workflow

## Overview
VeggaFresh supports two payment methods: **PhonePe (Online)** and **Cash on Delivery (COD)**. Orders are created at the time of payment initiation — not as a separate step.

---

## 1. Data Models

### OrderStatus (db_table: `order_status`)

Pre-seeded status names (managed via Django admin or fixtures):

| Status Name | Description |
|-------------|-------------|
| `Initiated` | PhonePe payment started |
| `Pending` | COD order placed, awaiting delivery |
| `Accepted` | Order accepted by store |
| `Assign to Delivery Partner` | Delivery partner assigned |
| `Out For Delivery` | On the way (triggers SMS to customer) |
| `Delivery Status Update` | Marked as delivered |
| `Completed` | PhonePe payment confirmed |
| `Failed` | PhonePe payment failed |
| `Cancelled` | Order cancelled |

---

### Order (db_table: `order`)

| Field | Type | Notes |
|-------|------|-------|
| `order_id` | CharField(20, unique) | Auto-generated: `YYMMDD<seq>` e.g. `260409001` |
| `user` | FK → User | Customer |
| `status` | FK → OrderStatus | Current status |
| `address` | FK → Address | Delivery address |
| `payment_method` | CharField | `'online'` or `'cod'` |
| `delivery_person` | FK → DeliveryPerson | Nullable |
| `tracking_link` | URLField | Tracking URL (nullable) |
| `created_at` | DateTimeField | Auto |

**`order.final_amount` (property):** Sums `price × quantity` for all OrderItems.

---

### OrderItem (db_table: `order_item`)

| Field | Type | Notes |
|-------|------|-------|
| `order` | FK → Order | Parent order |
| `product_variant` | FK → ProductVariant | What was ordered |
| `quantity` | PositiveIntegerField | How many units |

---

### Payment (db_table: via `payments` app)

| Field | Type | Notes |
|-------|------|-------|
| `order` | FK → Order | |
| `user` | FK → User | |
| `payment_id` | CharField | PhonePe transaction ID or `COD-<order_id>` |
| `transaction_id` | CharField | PhonePe transaction ID |
| `amount` | DecimalField | Order amount |
| `status` | CharField | `Pending` / `Completed` / `PAYMENT_SUCCESS` etc. |
| `raw_response` | JSONField | Full callback payload |
| `payment_date` | DateTimeField | Auto |

---

## 2. PhonePe Online Payment Flow

```
Customer                  Frontend                  Backend                  PhonePe
   |                         |                         |                        |
   |-- Add to cart --------->|                         |                        |
   |-- Select address ------>|                         |                        |
   |-- Click "Pay" --------->|                         |                        |
   |                         |-- POST /payment/create/ |                        |
   |                         |                         |-- Create Order          |
   |                         |                         |-- Create OrderItems     |
   |                         |                         |-- Clear Cart            |
   |                         |                         |-- Init PhonePe SDK ---->|
   |                         |                         |<-- redirectUrl ---------|
   |                         |<-- { redirectUrl } -----|                        |
   |<-- Redirect to PhonePe -|                         |                        |
   |-- Complete payment ---->|                        PhonePe                   |
   |                         |                         |<-- POST /payment/callback/
   |                         |                         |    Update Order status  |
   |                         |                         |    Create Payment record|
   |<-- Redirected back -----|                         |                        |
```

### POST /api/v1/payment/create/

```
Auth: Bearer <user_token>
```

```json
{ "address_id": 3 }
```

**Response:**

```json
{
  "message": "Payment initiated successfully.",
  "redirectUrl": "https://phonepe.com/checkout/...",
  "order_id": "260409001"
}
```

**What happens internally:**
1. Validates `address_id` belongs to user
2. Fetches user's cart (must not be empty)
3. Creates `Order` (status=`Initiated`) + `OrderItem` records
4. Calculates `final_amount` from cart
5. Converts to paise (×100) for PhonePe
6. Calls `StandardCheckoutClient.pay()` via PhonePe SDK
7. Clears cart immediately
8. Returns PhonePe `redirectUrl`

---

### POST /api/v1/payment/callback/ (PhonePe Webhook)

```
No Auth (called by PhonePe servers)
```

```json
{
  "merchantTransactionId": "260409001",
  "transactionId": "T2604...",
  "code": "PAYMENT_SUCCESS"
}
```

**What happens:**
- `PAYMENT_SUCCESS` → Order status = `Completed`, clear cart
- Otherwise → Order status = `Failed`
- Creates/updates `Payment` record with `raw_response`

---

## 3. Cash on Delivery (COD) Flow

### POST /api/v1/payment/cod/create/

```
Auth: Bearer <user_token>
```

```json
{ "address_id": 3 }
```

**Response:**

```json
{
  "message": "Order placed successfully with Cash on Delivery.",
  "order_id": "260409002",
  "payment_id": "COD-260409002",
  "amount": "450.00",
  "payment_status": "Pending"
}
```

**What happens:**
1. Validates address + non-empty cart
2. Creates `Order` (status=`Pending`, payment_method=`'cod'`)
3. Creates `OrderItem` records
4. Creates `Payment` record (status=`Pending`, id=`COD-<order_id>`)
5. Clears cart
6. Sends **Order Placed SMS** to customer's mobile

### PATCH /api/v1/payment/cod/{order_id}/collect/

Marks COD payment as collected once delivery is confirmed.

```
Auth: Admin with payment permission
```

```json
// Response
{
  "message": "COD payment collected successfully.",
  "order_id": "260409002",
  "payment_id": "COD-260409002",
  "amount": "450.00",
  "payment_status": "Completed"
}
```

---

## 4. Order Management (Admin)

### Update Order Status

```
PATCH /api/v1/orders/<id>/update-status/
Auth: Admin with order permission
```

```json
{ "status": <status_id> }
```

**SMS Trigger Map:**

| Status Set To | SMS Action |
|---------------|-----------|
| Out For Delivery | ✅ `send_out_for_delivery_sms()` to customer |
| All others | No SMS |

---

### Filter & Search Orders

```
GET /api/v1/orders-filters/
```

Supports DjangoFilter + search + ordering. See `orders/filters.py` for available filter fields.

---

### Order Status Workflow (Typical)

```
[Initiated / Pending]
       ↓
   [Accepted]
       ↓
[Assign to Delivery Partner]
       ↓
 [Out For Delivery]  ← SMS sent here
       ↓
[Delivery Status Update]
       ↓
   [Completed]
```

---

## 5. User Order APIs

### List My Orders

```
GET /api/v1/my-orders/
Auth: Bearer <user_token>
```

Returns all orders for the logged-in user, newest first, with full product image details.

---

### Order Detail

```
GET /api/v1/my-orders/<order_id>/
Auth: Bearer <user_token>
```

---

### Reorder (Add Past Order Items to Cart)

```
POST /api/v1/my-orders/<order_id>/reorder/
Auth: Bearer <user_token>
```

```json
// Response
{
  "message": "Items added to cart.",
  "added": ["Fresh Tomatoes", "Spinach"],
  "skipped": [
    { "product": "Out-of-Stock Item", "reason": "Out of stock or unavailable" }
  ],
  "cart": { ... }
}
```

- Available items are added back to cart (quantity accumulates if already in cart)
- Unavailable / out-of-stock variants are skipped

---

## 6. Analytics Endpoints

```
GET /api/v1/analytics/sales-per-month/    → Order count per month
GET /api/v1/analytics/most-sold-product/  → Top product this month
GET /api/v1/analytics/least-sold-product/ → Bottom product this month
GET /api/v1/analysis/sales-report/        → Daily/weekly/monthly breakdown
GET /api/v1/generate-sales-report/        → Export report as downloadable file
```

### Sales Report Response Structure

```json
{
  "daily":   {
    "total_orders": 5,
    "total_items_sold": 18,
    "total_revenue": 1200.00,
    "avg_order_value": 240.00,
    "top_selling_product": { "product_name": "...", "total_quantity_sold": 10, ... },
    "least_selling_product": { ... }
  },
  "weekly":  { ... },
  "monthly": { ... }
}
```

---

## 7. PhonePe SDK Configuration

Configured via `settings.PHONEPE_CONFIG`:

```python
PHONEPE_CONFIG = {
    'MERCHANT_ID': os.getenv('PHONEPE_MERCHANT_ID'),
    'CLIENT_ID': os.getenv('PHONEPE_CLIENT_ID'),
    'CLIENT_SECRET': os.getenv('PHONEPE_CLIENT_SECRET'),
    'BASE_URL': os.getenv('PHONEPE_BASE_URL'),
    'REDIRECT_URL': os.getenv('PHONEPE_REDIRECT_URL'),
}
```

Currently using `Env.SANDBOX` — change to `Env.PRODUCTION` when going live:

```python
# payments/views.py line ~71
client = StandardCheckoutClient.get_instance(
    client_id=settings.PHONEPE_CONFIG['CLIENT_ID'],
    client_secret=settings.PHONEPE_CONFIG['CLIENT_SECRET'],
    client_version=1,
    env=Env.PRODUCTION  # ← Change this for production
)
```

---

## 8. Delivery Person Management

```
GET    /api/v1/delivery-persons/        → List delivery persons
POST   /api/v1/delivery-persons/        → Add delivery person
GET    /api/v1/delivery-persons/<id>/   → Detail
PATCH  /api/v1/delivery-persons/<id>/   → Update
DELETE /api/v1/delivery-persons/<id>/   → Remove
```

| Field | Notes |
|-------|-------|
| `name` | Delivery person's name |
| `mobile` | Unique mobile (indexed) |

Assign to an order via status update or direct admin interface.
