import hashlib
import hmac
import uuid

import razorpay
from decimal import Decimal

from django.db import transaction
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from address.models import Address
from cart.models import Cart
from cart.serializers import CartSerializer
from orders.models import Order, OrderStatus, OrderItem
from svv_store import settings
from users.services import send_order_placed_sms
from .models import Payment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_razorpay_client():
    """Return an authenticated Razorpay client."""
    return razorpay.Client(
        auth=(settings.RAZORPAY_CONFIG['KEY_ID'], settings.RAZORPAY_CONFIG['KEY_SECRET'])
    )


def _verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, signature: str) -> bool:
    """
    Verify Razorpay payment signature.
    Formula: HMAC-SHA256(key=KEY_SECRET, msg="<razorpay_order_id>|<razorpay_payment_id>")
    """
    secret = settings.RAZORPAY_CONFIG['KEY_SECRET'].encode('utf-8')
    body = f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8')
    expected_signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


def _verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify Razorpay webhook signature.
    Formula: HMAC-SHA256(key=WEBHOOK_SECRET, msg=raw_request_body)
    """
    secret = settings.RAZORPAY_CONFIG['WEBHOOK_SECRET'].encode('utf-8')
    expected_signature = hmac.new(secret, payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)


def _complete_order_payment(order: Order, payment: Payment, razorpay_payment_id: str,
                            razorpay_signature: str = None, razorpay_response: dict = None):
    """
    Central helper: mark order Completed, update payment record, clear cart, send SMS.
    Called by both /verify/ and /webhook/ to ensure identical behaviour.
    Idempotent — safe to call multiple times for the same order.
    """
    if payment.status == 'Completed':
        return  # Already handled — nothing to do

    with transaction.atomic():
        # Update Payment record
        payment.status = 'Completed'
        payment.razorpay_payment_id = razorpay_payment_id
        if razorpay_signature:
            payment.razorpay_signature = razorpay_signature
        if razorpay_response:
            payment.razorpay_response = razorpay_response
        payment.save()

        # Update Order status
        completed_status, _ = OrderStatus.objects.get_or_create(name='Completed')
        order.status = completed_status
        order.save()

        # Clear cart
        try:
            cart = Cart.objects.get(user=order.user)
            cart.items.all().delete()
            cart.calculate_totals()
        except Cart.DoesNotExist:
            pass  # Cart may already be cleared

    # Send order confirmation SMS (outside transaction — non-critical)
    user = order.user
    if user and user.mobile:
        try:
            send_order_placed_sms(
                mobile=user.mobile,
                user_name=user.first_name or "Customer",
                order_id=order.order_id,
                total_amount=order.final_amount,
            )
        except Exception as e:
            print(f"[Razorpay] Order confirmation SMS failed for order {order.order_id}: {e}")


def _fail_order_payment(order: Order, payment: Payment, razorpay_response: dict = None):
    """Mark order and payment as Failed. Idempotent."""
    if payment.status in ('Completed', 'Failed'):
        return

    with transaction.atomic():
        payment.status = 'Failed'
        if razorpay_response:
            payment.razorpay_response = razorpay_response
        payment.save()

        failed_status, _ = OrderStatus.objects.get_or_create(name='Failed')
        order.status = failed_status
        order.save()


# ---------------------------------------------------------------------------
# View 1: Initiate Razorpay Payment
# POST /api/v1/payment/razorpay/create/
# ---------------------------------------------------------------------------

class InitiateRazorpayPayment(APIView):
    """
    Step 1 of the Razorpay flow.

    - Validates address + cart
    - Creates a DB Order with status=Initiated
    - Creates a Razorpay order via API
    - Saves a Payment record (status=Pending) linked to the order
    - Returns razorpay_order_id + key_id for the frontend Razorpay Checkout SDK

    The cart is NOT cleared here — it's cleared in _complete_order_payment()
    which is triggered by /verify/ (fast path) or /webhook/ (fallback).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # --- Validate address ---
        address_id = request.data.get('address_id')
        if not address_id:
            return Response(
                {"error": "address_id is required to place an order."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            address = Address.objects.get(id=address_id, user=user)
        except Address.DoesNotExist:
            return Response(
                {"error": "Address not found. Please add a delivery address."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Validate cart ---
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response({"error": "Cart does not exist."}, status=status.HTTP_404_NOT_FOUND)

        if not cart.items.exists():
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CartSerializer(cart)
        cart_details = serializer.data

        # --- Create Order in DB ---
        with transaction.atomic():
            initial_status, _ = OrderStatus.objects.get_or_create(name="Initiated")
            order = Order.objects.create(
                user=user,
                status=initial_status,
                payment_method='online',
                address=address,
                total_amount=cart.total_amount or Decimal('0.00'),
                taxes=cart.taxes or Decimal('0.00'),
                handling_charges=cart.handling_charges or Decimal('0.00'),
                delivery_charges=cart.delivery_charges or Decimal('0.00'),
                final_amount=cart.final_amount or Decimal('0.00'),
            )

            for item in cart.items.all():
                price_to_save = (
                    item.product_variant.discounted_price
                    if item.product_variant.discounted_price > 0
                    else item.product_variant.price
                )
                OrderItem.objects.create(
                    order=order,
                    product_variant=item.product_variant,
                    quantity=item.quantity,
                    price=price_to_save,
                )

        # --- Create Razorpay order ---
        final_amount = Decimal(cart_details['final_amount'])
        amount_paise = int(final_amount * 100)  # Razorpay expects amount in paise

        try:
            client = _get_razorpay_client()
            rz_order = client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": str(order.order_id),
                "payment_capture": 1,  # Auto-capture on payment
            })
        except Exception as e:
            # Roll back the DB order if Razorpay call fails
            order.delete()
            return Response(
                {"error": f"Failed to create Razorpay order: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # --- Save Payment record (Pending) ---
        payment_id = f"RZP-{order.order_id}-{uuid.uuid4().hex[:6].upper()}"
        Payment.objects.create(
            order=order,
            user=user,
            payment_id=payment_id,
            amount=final_amount,
            status='Pending',
            payment_gateway='razorpay',
            razorpay_order_id=rz_order['id'],
        )

        return Response({
            "message": "Razorpay order created successfully.",
            "order_id": order.order_id,
            "razorpay_order_id": rz_order['id'],
            "key_id": settings.RAZORPAY_CONFIG['KEY_ID'],
            "amount": amount_paise,
            "currency": "INR",
            "user_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "user_email": user.email or '',
            "user_mobile": str(user.mobile) if user.mobile else '',
        }, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# View 2: Verify Razorpay Payment (Frontend fast path)
# POST /api/v1/payment/razorpay/verify/
# ---------------------------------------------------------------------------

class RazorpayPaymentVerifyView(APIView):
    """
    Step 3 of the Razorpay flow (fast UI path).

    Frontend sends back the three values returned by Razorpay Checkout JS:
      - razorpay_order_id
      - razorpay_payment_id
      - razorpay_signature

    This view:
      1. Verifies HMAC-SHA256 signature
      2. Calls _complete_order_payment() which is idempotent
      3. Returns success immediately

    NOTE: The webhook (/razorpay/webhook/) is the true source of truth.
    If this endpoint is never called (user closes app), the webhook still
    completes the order. This view is purely for fast UI feedback.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response(
                {"error": "razorpay_order_id, razorpay_payment_id, and razorpay_signature are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Signature Verification ---
        if not _verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
            return Response(
                {"error": "Invalid payment signature. Payment verification failed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Fetch Payment record ---
        try:
            payment = Payment.objects.select_related('order', 'order__user').get(
                razorpay_order_id=razorpay_order_id
            )
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment record not found for this Razorpay order."},
                status=status.HTTP_404_NOT_FOUND
            )

        order = payment.order

        # --- Complete payment (idempotent) ---
        _complete_order_payment(
            order=order,
            payment=payment,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )

        return Response({
            "message": "Payment verified and order confirmed successfully.",
            "order_id": order.order_id,
            "payment_id": payment.payment_id,
            "amount": str(payment.amount),
            "status": "Completed",
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# View 3: Razorpay Webhook (Source of Truth)
# POST /api/v1/payment/razorpay/webhook/
# ---------------------------------------------------------------------------

class RazorpayWebhookView(APIView):
    """
    Razorpay server-to-server webhook — the real source of truth.

    Handles:
      - payment.captured  → marks payment Completed
      - order.paid        → marks payment Completed (duplicate event, idempotent)
      - payment.failed    → marks payment Failed

    Security:
      - Validates X-Razorpay-Signature header (HMAC-SHA256 of raw body)
      - No authentication required (Razorpay servers call this directly)

    Configure in Razorpay Dashboard:
      Settings → Webhooks → Add Webhook URL
      URL: https://yourdomain.com/api/v1/payment/razorpay/webhook/
      Secret: matches RAZORPAY_WEBHOOK_SECRET in .env
      Events: payment.captured, payment.failed, order.paid

    Razorpay retries webhooks with exponential backoff for up to 24 hours
    if this endpoint returns a non-2xx response.

    IMPORTANT: Uses only JSONParser so that request.body remains readable
    for HMAC signature verification (stream must not be pre-consumed).
    """
    authentication_classes = []  # No JWT — Razorpay servers call this
    permission_classes = []       # Webhook is secured by HMAC signature
    parser_classes = [JSONParser]  # Raw body must stay intact for HMAC check

    def post(self, request):
        # --- Webhook Signature Verification ---
        signature_header = request.headers.get('X-Razorpay-Signature', '')
        if not signature_header:
            return Response(
                {"error": "Missing X-Razorpay-Signature header."},
                status=status.HTTP_400_BAD_REQUEST
            )

        raw_body = request.body
        if not _verify_webhook_signature(raw_body, signature_header):
            return Response(
                {"error": "Invalid webhook signature."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Parse Payload ---
        try:
            payload = request.data  # DRF auto-parses JSON
        except Exception:
            return Response({"error": "Invalid JSON payload."}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get('event', '')
        entity = payload.get('payload', {})

        # --- Handle Events ---
        if event == 'payment.captured':
            return self._handle_payment_captured(entity)
        elif event == 'order.paid':
            return self._handle_order_paid(entity)
        elif event == 'payment.failed':
            return self._handle_payment_failed(entity)
        else:
            # Acknowledge unknown events — do not return 4xx (Razorpay would retry)
            return Response({"message": f"Event '{event}' received but not handled."}, status=status.HTTP_200_OK)

    def _handle_payment_captured(self, entity: dict):
        """payment.captured: payment was successfully captured by Razorpay."""
        payment_entity = entity.get('payment', {}).get('entity', {})
        razorpay_order_id = payment_entity.get('order_id')
        razorpay_payment_id = payment_entity.get('id')

        if not razorpay_order_id or not razorpay_payment_id:
            return Response({"error": "Missing order_id or payment_id in webhook payload."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.select_related('order', 'order__user').get(
                razorpay_order_id=razorpay_order_id
            )
        except Payment.DoesNotExist:
            # Return 200 to prevent Razorpay from retrying — record may not exist for other reasons
            print(f"[Webhook] Payment record not found for razorpay_order_id={razorpay_order_id}")
            return Response({"message": "Payment record not found. Acknowledged."}, status=status.HTTP_200_OK)

        _complete_order_payment(
            order=payment.order,
            payment=payment,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_response=payment_entity,
        )

        return Response({"message": "payment.captured handled successfully."}, status=status.HTTP_200_OK)

    def _handle_order_paid(self, entity: dict):
        """order.paid: fired after payment is captured. Acts as a backup to payment.captured."""
        order_entity = entity.get('order', {}).get('entity', {})
        payment_entity = entity.get('payment', {}).get('entity', {})
        razorpay_order_id = order_entity.get('id')
        razorpay_payment_id = payment_entity.get('id')

        if not razorpay_order_id or not razorpay_payment_id:
            return Response({"error": "Missing order/payment entity in webhook payload."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.select_related('order', 'order__user').get(
                razorpay_order_id=razorpay_order_id
            )
        except Payment.DoesNotExist:
            print(f"[Webhook] Payment record not found for razorpay_order_id={razorpay_order_id}")
            return Response({"message": "Payment record not found. Acknowledged."}, status=status.HTTP_200_OK)

        _complete_order_payment(
            order=payment.order,
            payment=payment,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_response=payment_entity,
        )

        return Response({"message": "order.paid handled successfully."}, status=status.HTTP_200_OK)

    def _handle_payment_failed(self, entity: dict):
        """payment.failed: payment attempt failed."""
        payment_entity = entity.get('payment', {}).get('entity', {})
        razorpay_order_id = payment_entity.get('order_id')

        if not razorpay_order_id:
            return Response({"error": "Missing order_id in payment.failed payload."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.select_related('order').get(
                razorpay_order_id=razorpay_order_id
            )
        except Payment.DoesNotExist:
            print(f"[Webhook] Payment record not found for razorpay_order_id={razorpay_order_id}")
            return Response({"message": "Payment record not found. Acknowledged."}, status=status.HTTP_200_OK)

        _fail_order_payment(
            order=payment.order,
            payment=payment,
            razorpay_response=payment_entity,
        )

        return Response({"message": "payment.failed handled successfully."}, status=status.HTTP_200_OK)
