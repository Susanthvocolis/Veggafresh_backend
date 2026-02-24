from django.db.models.functions import TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Count, F
from orders.models import Order, OrderItem
from products.models import ProductVariant
from datetime import timedelta


class SalesPerMonthView(APIView):
    def get(self, request):
        sales_data = (
            Order.objects
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(order_count=Count('id'))
            .order_by('month')
        )
        return Response(sales_data)


class MostSoldProductOfMonth(APIView):
    def get(self, request):
        now = timezone.now()
        start_of_month = now.replace(day=1)

        items = (
            OrderItem.objects
            .filter(order__created_at__gte=start_of_month)
            .values('product_variant')
            .annotate(total_quantity=Sum('quantity'))
            .order_by('-total_quantity')
        )

        if not items:
            return Response([])

        top_item = items[0]
        variant = ProductVariant.objects.select_related('product').get(id=top_item['product_variant'])

        data = {
            "product_name": variant.product.name,
            "product_id": variant.product.id,
            "variant_id": variant.id,
            "variant_quantity": f"{variant.quantity} {variant.unit}",
            "price": str(variant.price),
            "discounted_price": str(variant.discounted_price) if variant.discounted_price else None,
            "total_quantity_sold": top_item['total_quantity']
        }

        return Response(data)

class LeastSoldProductOfMonth(APIView):
    def get(self, request):
        now = timezone.now()
        start_of_month = now.replace(day=1)

        least_sold = (
            OrderItem.objects
            .filter(order__created_at__gte=start_of_month)
            .values('product_variant')
            .annotate(total_quantity=Sum('quantity'))
            .order_by('total_quantity')
            .first()
        )

        if not least_sold:
            return Response(None)

        from products.models import ProductVariant  # Import here to avoid circular imports if needed
        variant = ProductVariant.objects.select_related('product').get(id=least_sold['product_variant'])

        data = {
            "product_id": variant.product.id,
            "product_name": variant.product.name,
            "variant_id": variant.id,
            "variant_quantity": f"{variant.quantity} {variant.unit}",
            "price": str(variant.price),
            "discounted_price": str(variant.discounted_price) if variant.discounted_price else None,
            "total_quantity_sold": least_sold['total_quantity']
        }

        return Response(data)



class SalesReportView(APIView):
    def get(self, request):
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)

        def get_sales_data(start_date):
            orders = Order.objects.filter(created_at__date__gte=start_date)
            order_items = OrderItem.objects.filter(order__in=orders)

            total_orders = orders.count()
            total_items_sold = order_items.aggregate(total=Sum('quantity'))['total'] or 0

            total_revenue = order_items.aggregate(
                revenue=Sum(F('quantity') * F('product_variant__discounted_price'))
            )['revenue'] or 0

            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

            # Top selling product
            top_product_data = (
                order_items
                .values(
                    product_id=F('product_variant__product__id'),
                    product_name=F('product_variant__product__name'),
                    variant_id=F('product_variant__id'),
                    variant_quantity=F('product_variant__quantity'),
                    unit=F('product_variant__unit'),
                    price=F('product_variant__price'),
                    discounted_price=F('product_variant__discounted_price'),
                )
                .annotate(total_quantity_sold=Sum('quantity'))
                .order_by('-total_quantity_sold')
                .first()
            )

            # Least selling product
            least_product_data = (
                order_items
                .values(
                    product_id=F('product_variant__product__id'),
                    product_name=F('product_variant__product__name'),
                    variant_id=F('product_variant__id'),
                    variant_quantity=F('product_variant__quantity'),
                    unit=F('product_variant__unit'),
                    price=F('product_variant__price'),
                    discounted_price=F('product_variant__discounted_price'),
                )
                .annotate(total_quantity_sold=Sum('quantity'))
                .order_by('total_quantity_sold')
                .first()
            )

            return {
                "total_orders": total_orders,
                "total_items_sold": total_items_sold,
                "total_revenue": float(total_revenue),
                "avg_order_value": round(avg_order_value, 2),
                "top_selling_product": top_product_data,
                "least_selling_product": least_product_data,
            }

        data = {
            "daily": get_sales_data(today),
            "weekly": get_sales_data(start_of_week),
            "monthly": get_sales_data(start_of_month),
        }

        return Response(data)
