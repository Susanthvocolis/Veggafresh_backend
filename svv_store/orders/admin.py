from django.contrib import admin
from .models import Order, OrderStatus, OrderItem, DeliveryPerson

from django.contrib import admin
from .models import Order, OrderStatus, OrderItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_id', 'user', 'status',
        'get_delivery_boy_name', 'get_delivery_boy_mobile',  # updated here
        'created_at'
    )

    def get_delivery_boy_name(self, obj):
        return obj.delivery_person.name if obj.delivery_person else "-"
    get_delivery_boy_name.short_description = 'Delivery Boy Name'

    def get_delivery_boy_mobile(self, obj):
        return obj.delivery_person.mobile if obj.delivery_person else "-"
    get_delivery_boy_mobile.short_description = 'Delivery Boy Mobile'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order_id', 'order_user', 'product_variant',
        'quantity', 'order_status', 'order_created_at'
    )
    search_fields = (
        'order__id',
        'product_variant__product__name',
        'order__user__email',
        'order__user__first_name'
    )
    list_select_related = ('order', 'product_variant')
    ordering = ('-order__created_at',)  # Order by order's creation date

    def order_id(self, obj):
        return obj.order.id

    order_id.short_description = 'Order ID'
    order_id.admin_order_field = 'order__id'

    def order_user(self, obj):
        return obj.order.user

    order_user.short_description = 'User'
    order_user.admin_order_field = 'order__user'

    def order_status(self, obj):
        return obj.order.status

    order_status.short_description = 'Order Status'
    order_status.admin_order_field = 'order__status'

    def order_created_at(self, obj):
        return obj.order.created_at

    order_created_at.short_description = 'Order Date'
    order_created_at.admin_order_field = 'order__created_at'

@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    search_fields = ('name',)

@admin.register(DeliveryPerson)
class DeliveryPersonAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'mobile']
    search_fields = ['name', 'mobile']
