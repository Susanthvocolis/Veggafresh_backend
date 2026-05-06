from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['payment_date', 'status', 'phonepe_response', 'phonepe_transaction_id']


class RazorpayVerifySerializer(serializers.Serializer):
    """Input serializer for POST /payment/razorpay/verify/"""
    razorpay_order_id = serializers.CharField(required=True)
    razorpay_payment_id = serializers.CharField(required=True)
    razorpay_signature = serializers.CharField(required=True)


class EmpPaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_id',
            'order_id',
            'user_id',
            'user_email',
            'amount',
            'status',
            'payment_gateway',
            'payment_date',
            # Razorpay fields
            'razorpay_order_id',
            'razorpay_payment_id',
        ]
