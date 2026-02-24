from django.urls import reverse
from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
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

class InitiatePhonePePayment(APIView):
    def post(self, request):
        user = request.user
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
        order = Order.objects.create(user=user, status=initial_status)

        # Create OrderItems from CartItems
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product_variant=item.product_variant,
                quantity=item.quantity
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



class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('-payment_date')
    serializer_class = EmpPaymentSerializer
    permission_classes = [IsSuperAdminOrHasPaymentPermission]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PaymentFilter
    search_fields = ['payment_id', 'order__id']
    ordering_fields = ['payment_date']