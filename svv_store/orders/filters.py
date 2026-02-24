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
            'status',
            'order_id',  # Include in fields list
        ]

