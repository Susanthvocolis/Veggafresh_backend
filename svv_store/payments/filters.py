import django_filters
from .models import Payment

class PaymentFilter(django_filters.FilterSet):
    payment_date = django_filters.DateFilter(field_name='payment_date', lookup_expr='date')
    payment_date_from = django_filters.DateFilter(field_name='payment_date', lookup_expr='gte', label='From Date')
    payment_date_to = django_filters.DateFilter(field_name='payment_date', lookup_expr='lte', label='To Date')

    class Meta:
        model = Payment
        fields = ['status', 'payment_date', 'user__id', 'order__id']
