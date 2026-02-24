from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['payment_date', 'status', 'phonepe_response', 'phonepe_transaction_id']

class EmpPaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.id', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)  # 👈 Add this line

    class Meta:
        model = Payment
        fields = ['id', 'payment_id', 'order_id', 'user_id', 'user_email', 'amount', 'status', 'payment_date']
