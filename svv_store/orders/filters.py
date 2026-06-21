import django_filters
from .models import Order
from users.models import User

class OrderFilter(django_filters.FilterSet):
    # Filtering on related fields (user)
    user_id = django_filters.NumberFilter(field_name='user__id', lookup_expr='exact')
    user_email = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    user_mobile = django_filters.CharFilter(field_name='user__mobile', lookup_expr='icontains')

    # Filtering on date range (created_at)
    order_date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    order_date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    delivery_date = django_filters.DateFilter(field_name='delivery_date', lookup_expr='exact')
    delivery_date_from = django_filters.DateFilter(field_name='delivery_date', lookup_expr='gte')
    delivery_date_to = django_filters.DateFilter(field_name='delivery_date', lookup_expr='lte')
    delivery_slot = django_filters.CharFilter(field_name='delivery_slot_name', lookup_expr='icontains')
    delivery_slot_id = django_filters.NumberFilter(field_name='delivery_schedule__slot__id', lookup_expr='exact')
    delivery_schedule_id = django_filters.NumberFilter(field_name='delivery_schedule__id', lookup_expr='exact')

    # Filtering on status
    status = django_filters.CharFilter(field_name='status__name', lookup_expr='icontains')

    # Filtering on order_id
    order_id = django_filters.CharFilter(field_name='order_id', lookup_expr='icontains')

    class Meta:
        model = Order
        fields = [
            'user_id',
            'user_email',
            'user_mobile',
            'order_date_from',
            'order_date_to',
            'delivery_date',
            'delivery_date_from',
            'delivery_date_to',
            'delivery_slot',
            'delivery_slot_id',
            'delivery_schedule_id',
            'status',
            'order_id',  # Include in fields list
        ]

