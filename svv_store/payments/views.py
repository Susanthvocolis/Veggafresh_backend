from django.urls import reverse
from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
from address.models import Address
from cart.models import Cart
from cart.serializers import CartSerializer
from svv_store import settings
from .filters import PaymentFilter
from .permissions import IsSuperAdminOrHasPaymentPermission
from rest_framework import status, viewsets
from .serializers import EmpPaymentSerializer
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Payment
from orders.models import Order, OrderStatus, OrderItem
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from phonepe.sdk.pg.env import Env
from users.services import send_order_placed_sms

class InitiatePhonePePayment(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Validate address
        address_id = request.data.get('address_id')
        if not address_id:
            return Response({"error": "address_id is required to place an order."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            address = Address.objects.get(id=address_id, user=user)
        except Address.DoesNotExist:
            return Response({"error": "Address not found. Please add a delivery address."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response({"error": "Cart does not exist."}, status=status.HTTP_404_NOT_FOUND)

        if not cart.items.exists():
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CartSerializer(cart)
        cart_details = serializer.data

        # 1. Create Order
        initial_status, _ = OrderStatus.objects.get_or_create(name="Initiated")
        order = Order.objects.create(
            user=user, 
            status=initial_status, 
            address=address,
            total_amount=cart.total_amount,
            taxes=cart.taxes,
            handling_charges=cart.handling_charges,
            delivery_charges=cart.delivery_charges,
            final_amount=cart.final_amount
        )

        # Create OrderItems from CartItems
        for item in cart.items.all():
            price_to_save = item.product_variant.discounted_price if item.product_variant.discounted_price > 0 else item.product_variant.price
            OrderItem.objects.create(
                order=order,
                product_variant=item.product_variant,
                quantity=item.quantity,
                price=price_to_save
            )

        # 2. Calculate total amount
        total_amount = Decimal(cart_details['final_amount'])  # Assuming your CartSerializer gives this
        amount_paise = int(total_amount * Decimal('100'))  # PhonePe needs amount in paise

        # 3. Init PhonePe SDK
        client = StandardCheckoutClient.get_instance(
            client_id=settings.PHONEPE_CONFIG['CLIENT_ID'],
            client_secret=settings.PHONEPE_CONFIG['CLIENT_SECRET'],
            client_version=1,  # use the correct client version
            env=Env.SANDBOX  # use Env.PRODUCTION when live
        )
        callback_url = request.build_absolute_uri(reverse('phonepe-callback'))
        # 4. Build payment request
        merchant_order_id = str(order.order_id)
        redirect_url = settings.PHONEPE_CONFIG['REDIRECT_URL']
        pay_request = StandardCheckoutPayRequest.build_request(
            merchant_order_id=merchant_order_id,
            amount=amount_paise,
            redirect_url=redirect_url
        )

        # 5. Send payment request
        pay_response = client.pay(pay_request)

        # 6. Clear cart after creating payment request
        cart.items.all().delete()
        cart.calculate_totals()

        # 7. Return redirect URL to frontend
        return Response({
            "message": "Payment initiated successfully.",
            "redirectUrl": pay_response.redirect_url,
            "order_id": order.order_id
        }, status=status.HTTP_200_OK)




class PhonePeCallbackView(APIView):
    authentication_classes = []  # No Auth
    permission_classes = []       # No Permission

    def post(self, request):
        try:
            data = json.loads(request.body)

            merchant_transaction_id = data.get('merchantTransactionId')
            transaction_id = data.get('transactionId')
            status_code = data.get('code')  # "PAYMENT_SUCCESS" or "PAYMENT_ERROR" etc

            # Find Order
            order = Order.objects.get(order_id=merchant_transaction_id)

            if status_code == "PAYMENT_SUCCESS":
                completed_status, _ = OrderStatus.objects.get_or_create(name="Completed")
                order.status = completed_status
                try:
                    cart = Cart.objects.get(user=order.user)
                    cart.items.all().delete()
                    cart.calculate_totals()
                except Cart.DoesNotExist:
                    pass
            else:
                failed_status, _ = OrderStatus.objects.get_or_create(name="Failed")
                order.status = failed_status

            order.save()

            # Create/Update Payment record
            Payment.objects.update_or_create(
                order=order,
                defaults={
                    "transaction_id": transaction_id,
                    "amount": order.final_amount,
                    "status": status_code,
                    "raw_response": data
                }
            )

            return Response({"message": "Callback processed."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class CodOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Validate address
        address_id = request.data.get('address_id')
        if not address_id:
            return Response({"error": "address_id is required to place an order."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            address = Address.objects.get(id=address_id, user=user)
        except Address.DoesNotExist:
            return Response({"error": "Address not found. Please add a delivery address."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response({"error": "Cart does not exist."}, status=status.HTTP_404_NOT_FOUND)

        if not cart.items.exists():
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        # Create order
        pending_status, _ = OrderStatus.objects.get_or_create(name="Pending")
        order = Order.objects.create(
            user=user, 
            status=pending_status, 
            payment_method='cod', 
            address=address,
            total_amount=cart.total_amount,
            taxes=cart.taxes,
            handling_charges=cart.handling_charges,
            delivery_charges=cart.delivery_charges,
            final_amount=cart.final_amount
        )

        for item in cart.items.all():
            price_to_save = item.product_variant.discounted_price if item.product_variant.discounted_price > 0 else item.product_variant.price
            OrderItem.objects.create(
                order=order,
                product_variant=item.product_variant,
                quantity=item.quantity,
                price=price_to_save
            )

        total_amount = order.final_amount

        # Create Payment record for COD
        payment = Payment.objects.create(
            order=order,
            user=user,
            payment_id=f"COD-{order.order_id}",
            amount=total_amount,
            status='Pending'
        )

        # Clear cart
        cart.items.all().delete()
        cart.calculate_totals()

        # Send SMS
        if user.mobile:
            try:
                send_order_placed_sms(
                    mobile=user.mobile,
                    user_name=user.first_name or "Customer",
                    order_id=order.order_id,
                    total_amount=total_amount,
                )
            except Exception as e:
                print(f"COD order SMS failed: {e}")

        return Response({
            "message": "Order placed successfully with Cash on Delivery.",
            "order_id": order.order_id,
            "payment_id": payment.payment_id,
            "amount": str(total_amount),
            "payment_status": payment.status,
        }, status=status.HTTP_201_CREATED)


class CodCollectView(APIView):
    permission_classes = [IsSuperAdminOrHasPaymentPermission]

    def patch(self, request, order_id):
        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_method != 'cod':
            return Response({"error": "This order is not a COD order."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(order=order)
        except Payment.DoesNotExist:
            return Response({"error": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == 'Completed':
            return Response({"error": "Payment already collected."}, status=status.HTTP_400_BAD_REQUEST)

        payment.status = 'Completed'
        payment.save()

        return Response({
            "message": "COD payment collected successfully.",
            "order_id": order.order_id,
            "payment_id": payment.payment_id,
            "amount": str(payment.amount),
            "payment_status": payment.status,
        }, status=status.HTTP_200_OK)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('-payment_date')
    serializer_class = EmpPaymentSerializer
    permission_classes = [IsSuperAdminOrHasPaymentPermission]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PaymentFilter
    search_fields = ['payment_id', 'order__id']
    ordering_fields = ['payment_date', 'amount', 'status']
    ordering = ['-payment_date']