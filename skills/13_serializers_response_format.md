# Skill: Serializers & API Response Format

## Overview

VeggaFresh uses DRF serializers for all data in/out and a `CustomRenderer` that wraps every response in a standard envelope. Understanding both is essential for consistent API behaviour.

---

## 1. Custom Response Envelope (`CustomRenderer`)

Located at `utils/renderers.py`. **Every** API response is automatically wrapped:

```json
{
  "message": "Success",
  "data": { ... },
  "status_code": 200
}
```

On error:
```json
{
  "message": "Failed",
  "data": { "field": ["This field is required."] },
  "status_code": 400
}
```

You do **not** need to manually wrap responses — just `return Response(data)` and the renderer handles it.

---

## 2. Serializer Patterns Used in This Project

### Basic `ModelSerializer`

```python
class DeliveryPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPerson
        fields = ['id', 'name', 'mobile']
```

### `StringRelatedField` — show `__str__` of a related model

```python
class OrderSerializer(serializers.ModelSerializer):
    user   = serializers.StringRelatedField()   # shows user.__str__ (email)
    status = serializers.StringRelatedField()   # shows status.__str__ (name)
```

### `SerializerMethodField` — computed / custom fields

```python
class OrderItemSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        image = obj.product_variant.product.images.first()
        return image.image if image else None
```

### Nested serializer — embed a full object

```python
class OrderSerializer(serializers.ModelSerializer):
    delivery_person = DeliveryPersonSerializer(read_only=True)
    address         = AddressSerializer(read_only=True)
    items           = OrderItemSerializer(many=True, read_only=True)
```

### `source` — map to a different field/relation

```python
product_name  = serializers.CharField(source='product_variant.product.name', read_only=True)
price         = serializers.DecimalField(source='product_variant.price', max_digits=10, decimal_places=2)
```

### `PrimaryKeyRelatedField` — write with an ID, read as object

```python
class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    status = serializers.PrimaryKeyRelatedField(queryset=OrderStatus.objects.all())

    class Meta:
        model  = Order
        fields = ['status']
```

---

## 3. Creating Admin vs User Serializers (Different Response Shapes)

When the admin and user need different fields from the same model:

```python
# Full serializer (user-facing — includes product_image)
class OrderItemSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()
    ...

# Lean serializer (admin-facing — no product_image for speed)
class AdminOrderItemSerializer(serializers.ModelSerializer):
    # product_image removed
    ...

class AdminOrderSerializer(serializers.ModelSerializer):
    items = AdminOrderItemSerializer(many=True, read_only=True)  # ← use lean
    ...
```

Then use `AdminOrderSerializer` in admin views and `OrderSerializer` in user views.

---

## 4. Caching Payment Data Within a Serializer

Avoid duplicate DB hits per item with `_cached_payment`:

```python
class OrderSerializer(serializers.ModelSerializer):
    payment_status = serializers.SerializerMethodField()
    payment_amount = serializers.SerializerMethodField()

    def _get_payment(self, obj):
        if not hasattr(obj, '_cached_payment'):
            obj._cached_payment = Payment.objects.filter(order=obj).first()
        return obj._cached_payment

    def get_payment_status(self, obj):
        payment = self._get_payment(obj)
        return payment.status if payment else None

    def get_payment_amount(self, obj):
        payment = self._get_payment(obj)
        return payment.amount if payment else None
```

---

## 5. Write Serializer (Create with Nested Items)

```python
class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)

    class Meta:
        model  = Order
        fields = ['items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        status     = OrderStatus.objects.get(name="Pending")
        order      = Order.objects.create(status=status, **validated_data)

        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order
```

---

## 6. Partial Update (`partial=True`)

```python
serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
if serializer.is_valid():
    serializer.save()
```

Use `partial=True` when only some fields are being updated (PATCH).

---

## 7. Passing Extra Data on Save

```python
# In a ViewSet's perform_create:
def perform_create(self, serializer):
    serializer.save(user=self.request.user)  # inject user from request
```

---

## 8. Common Serializer Mistakes

| Mistake | Fix |
|---|---|
| `read_only=True` missing on nested serializers | Add `read_only=True` to nested fields |
| `N+1 queries` on nested data | Use `select_related` / `prefetch_related` in the queryset |
| `WritableField` on a computed value | Use `SerializerMethodField` for read-only computed values |
| Serializer not validating | Call `serializer.is_valid(raise_exception=True)` instead of checking manually |
| Decimal shows as string | Use `serializers.DecimalField(max_digits=10, decimal_places=2)` |
